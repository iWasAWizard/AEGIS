# aegis/executors/redis_exec.py
"""
Redis executor with cautious logging and ToolResult wrappers.

Requires: redis (redis-py)
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple, Union
import json
import time

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log

logger = setup_logger(__name__)

try:
    import redis
    from redis.exceptions import (
        TimeoutError as RedisTimeout,
        AuthenticationError,
        ConnectionError as RedisConnError,
        ResponseError,
        RedisError,
    )

    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False


def _now_ms() -> int:
    return int(time.time() * 1000)


def _sanitize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    # redact password if present: redis://user:pass@host:port/db
    try:
        if "@" in url and "://" in url and ":" in url.split("@")[0]:
            scheme, rest = url.split("://", 1)
            left, right = rest.split("@", 1)
            if ":" in left:
                user, _pwd = left.split(":", 1)
                return f"{scheme}://{user}:********@{right}"
    except Exception:
        pass
    return url


def _errtype(e: Exception) -> str:
    if isinstance(e, RedisTimeout):
        return "Timeout"
    if isinstance(e, AuthenticationError):
        return "Auth"
    if isinstance(e, RedisConnError):
        # network/connectivity
        return "Runtime"
    if isinstance(e, ResponseError):
        return "Parse"  # script/protocol-level issues resemble parse class
    return "Runtime"


class RedisExecutor:
    """Lightweight wrapper around redis-py with safer logging."""

    def __init__(
        self,
        url: Optional[str] = None,
        *,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        socket_timeout: float = 5.0,
        decode_responses: bool = True,
    ):
        """
        Either supply a redis URL or discrete host/port/db creds.

        :param url: e.g. redis://[:password]@host:port/db
        :param host: host (ignored if url is provided)
        :param port: port (ignored if url is provided)
        :param db: database index (ignored if url is provided)
        :param password: password (ignored if url is provided)
        :param ssl: use TLS when not using url
        :param socket_timeout: request timeout in seconds
        :param decode_responses: return strings instead of bytes
        """
        if not REDIS_AVAILABLE:
            raise ConfigurationError("The 'redis' Python package is not installed.")
        try:
            if url:
                self.client = redis.Redis.from_url(
                    url,
                    socket_timeout=socket_timeout,
                    decode_responses=decode_responses,
                )
                logger.info("Connected to Redis", extra={"url": _sanitize_url(url)})
            else:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    ssl=ssl,
                    socket_timeout=socket_timeout,
                    decode_responses=decode_responses,
                )
                logger.info(
                    "Connected to Redis",
                    extra={
                        "host": host,
                        "port": port,
                        "db": db,
                        "ssl": ssl,
                    },
                )
            # quick ping to fail fast
            self.client.ping()
        except RedisError as e:
            raise ToolExecutionError(f"Redis connection error: {e}") from e

    # --- Core ops ---

    def ping(self) -> bool:
        return bool(self.client.ping())

    def get(self, key: str) -> Optional[str]:
        return self.client.get(key)

    def set(
        self,
        key: str,
        value: Union[str, bytes, int, float],
        *,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        return bool(self.client.set(name=key, value=value, ex=ex, px=px, nx=nx, xx=xx))

    def delete(self, *keys: str) -> int:
        return int(self.client.delete(*keys))

    def keys(self, pattern: str = "*") -> List[str]:
        # SCAN would be safer for huge DBs; for executor simplicity keep KEYS
        out = self.client.keys(pattern)
        return list(out or [])

    def hgetall(self, key: str) -> Dict[str, str]:
        return dict(self.client.hgetall(key) or {})

    def expire(self, key: str, seconds: int) -> bool:
        return bool(self.client.expire(key, seconds))

    def eval(
        self,
        script: str,
        keys: Optional[List[str]] = None,
        args: Optional[List[Any]] = None,
    ) -> Any:
        keys = keys or []
        args = args or []
        return self.client.eval(script, len(keys), *(keys + args))


# === ToolResult wrappers ===


class RedisExecutorToolResultMixin:
    def ping_result(self) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(tool="redis.ping", args={})
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.ping",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            ok = self.ping()
            return ToolResult.ok_result(
                stdout="PONG" if ok else "NO-RESPONSE",
                exit_code=0,
                latency_ms=_now_ms() - start,
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
            )

    def get_result(self, key: str) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.get", args=redact_for_log({"key": key})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.get",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            val = self.get(key)
            return ToolResult.ok_result(
                stdout="" if val is None else str(val),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"key": key, "miss": val is None},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"key": key},
            )

    def set_result(
        self,
        key: str,
        value: Union[str, bytes, int, float],
        *,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.set",
                args=redact_for_log(
                    {
                        "key": key,
                        "value": "<redacted>",
                        "ex": ex,
                        "px": px,
                        "nx": nx,
                        "xx": xx,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.set",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            ok = self.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
            return ToolResult.ok_result(
                stdout="OK" if ok else "NOSET",
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"key": key, "set": ok},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"key": key},
            )

    def delete_result(self, *keys: str) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.del", args=redact_for_log({"keys": list(keys)})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.del",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            n = self.delete(*keys)
            return ToolResult.ok_result(
                stdout=str(n),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"deleted": n, "keys": list(keys)},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"keys": list(keys)},
            )

    def keys_result(self, pattern: str = "*") -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.keys", args=redact_for_log({"pattern": pattern})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.keys",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            arr = self.keys(pattern)
            return ToolResult.ok_result(
                stdout=json.dumps(arr),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"pattern": pattern, "count": len(arr)},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"pattern": pattern},
            )

    def hgetall_result(self, key: str) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.hgetall", args=redact_for_log({"key": key})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.hgetall",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            m = self.hgetall(key)
            return ToolResult.ok_result(
                stdout=json.dumps(m),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"key": key, "size": len(m)},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"key": key},
            )

    def expire_result(self, key: str, seconds: int) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.expire",
                args=redact_for_log({"key": key, "seconds": seconds}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.expire",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            ok = self.expire(key, seconds)
            return ToolResult.ok_result(
                stdout="OK" if ok else "NOEXP",
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"key": key, "seconds": seconds, "applied": ok},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"key": key, "seconds": seconds},
            )

    def eval_result(
        self,
        script: str,
        keys: Optional[List[str]] = None,
        args: Optional[List[Any]] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.eval",
                args=redact_for_log(
                    {"script": "<redacted>", "keys": keys or [], "args": args or []}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.eval",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.eval(script, keys=keys, args=args)
            # JSON-encode complex outputs for consistency
            try:
                stdout = json.dumps(out)
            except Exception:
                stdout = str(out)
            return ToolResult.ok_result(
                stdout=stdout,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"keys": keys or [], "args_len": len(args or [])},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"keys": keys or [], "args_len": len(args or [])},
            )


# bind mixin
RedisExecutor.ping_result = RedisExecutorToolResultMixin.ping_result
RedisExecutor.get_result = RedisExecutorToolResultMixin.get_result
RedisExecutor.set_result = RedisExecutorToolResultMixin.set_result
RedisExecutor.delete_result = RedisExecutorToolResultMixin.delete_result
RedisExecutor.keys_result = RedisExecutorToolResultMixin.keys_result
RedisExecutor.hgetall_result = RedisExecutorToolResultMixin.hgetall_result
RedisExecutor.expire_result = RedisExecutorToolResultMixin.expire_result
RedisExecutor.eval_result = RedisExecutorToolResultMixin.eval_result
