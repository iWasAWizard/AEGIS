# aegis/executors/redis_exec.py
"""
Provides a client for Redis operations via redis-py.
"""
from typing import Optional

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time
from aegis.utils.exec_common import (
    now_ms as _common_now_ms,
    map_exception_to_error_type as _common_map_error,
)

logger = setup_logger(__name__)

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisExecutor:
    """A simple client for Redis key/value operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: int = 5,
    ):
        """
        Initialize the Redis executor.

        :param host: Redis host address.
        :type host: str
        :param port: Redis port number.
        :type port: int
        :param db: Redis database index.
        :type db: int
        :param password: Optional password for Redis.
        :type password: Optional[str]
        :param socket_timeout: Socket timeout for Redis operations in seconds.
        :type socket_timeout: int
        """
        if not REDIS_AVAILABLE:
            raise ToolExecutionError("The 'redis' library is not installed.")
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=socket_timeout,
                decode_responses=True,
            )
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}/{db}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ToolExecutionError(f"Failed to connect to Redis: {e}") from e

    def set_value(self, key: str, value: str, expire_s: int | None = None) -> bool:
        """
        Set a value for a key in Redis with optional expiry.

        :param key: Redis key.
        :type key: str
        :param value: Value to set for the key.
        :type value: str
        :param expire_s: Expiration time in seconds, or None for no expiration.
        :type expire_s: Optional[int]
        :return: True if the command was accepted.
        :rtype: bool
        """
        try:
            if expire_s is not None:
                return bool(self.client.setex(key, expire_s, value))
            return bool(self.client.set(key, value))
        except Exception as e:
            raise ToolExecutionError(f"Redis error (set): {e}") from e

    def get_value(self, key: str) -> str | None:
        """
        Retrieve the value of a key from Redis.

        :param key: Redis key to retrieve.
        :type key: str
        :return: The value as a string, or None if key does not exist.
        :rtype: Optional[str]
        """
        try:
            return self.client.get(key)
        except Exception as e:
            raise ToolExecutionError(f"Redis error (get): {e}") from e

    def delete_value(self, key: str) -> bool:
        """
        Delete a key from Redis.

        :param key: Redis key to delete.
        :type key: str
        :return: True if a key was deleted, False otherwise.
        :rtype: bool
        """
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            raise ToolExecutionError(f"Redis error (delete): {e}") from e


# === ToolResult wrappers ===
def _now_ms() -> int:
    # Delegate to shared clock for consistency/testability
    return _common_now_ms()


def _error_type_from_exception(e: Exception) -> str:
    """
    Preserve existing labels while consulting the shared mapper for consistency.
    """
    msg = str(e).lower()
    mapped = (_common_map_error(e) or "").lower()

    if "timeout" in msg or mapped == "timeout":
        return "Timeout"
    if "permission" in msg or "auth" in msg or mapped == "permission_denied":
        return "Auth"
    if "not found" in msg or "no such" in msg or mapped == "not_found":
        return "NotFound"
    if "parse" in msg or "json" in msg:
        return "Parse"
    # Fall back to prior default
    return "Runtime"


class RedisExecutorToolResultMixin:
    def set_value_result(
        self, key: str, value: str, expire_s: int | None = None
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.set",
                args=redact_for_log({"key": key, "expire_s": expire_s}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.set",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.set_value(key=key, value=value, expire_s=expire_s)
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"key": key, "expire_s": expire_s},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"key": key, "expire_s": expire_s},
            )

    def get_value_result(self, key: str) -> ToolResult:
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
            out = self.get_value(key=key)
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"key": key},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"key": key},
            )

    def delete_value_result(self, key: str) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="redis.del", args=redact_for_log({"key": key})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] redis.del",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.delete_value(key=key)
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"key": key},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"key": key},
            )


RedisExecutor.set_value_result = RedisExecutorToolResultMixin.set_value_result
RedisExecutor.get_value_result = RedisExecutorToolResultMixin.get_value_result
RedisExecutor.delete_value_result = RedisExecutorToolResultMixin.delete_value_result
