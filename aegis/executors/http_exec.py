# aegis/executors/http_exec.py
"""
Provides a client for making HTTP requests with safe logging and ToolResult wrappers.
"""
from __future__ import annotations

from typing import Optional, Dict, Any

import httpx
from aegis.utils.http_client import HttpClient, DEFAULT_TIMEOUT
from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time
import asyncio

logger = setup_logger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _error_type_from_exception(e: Exception) -> str:
    msg = str(e).lower()
    if "timeout" in msg:
        return "Timeout"
    if "permission" in msg or "auth" in msg:
        return "Auth"
    if "not found" in msg or "404" in msg:
        return "NotFound"
    if "parse" in msg or "json" in msg:
        return "Parse"
    return "Runtime"


class HttpExecutor:
    """A client for making HTTP requests consistently."""

    def __init__(self, base_url: Optional[str] = None, default_timeout: int = 30):
        self.base_url = base_url
        # Build shared sync/async clients once; caller wrappers cleanly use them.
        t = httpx.Timeout(
            connect=5.0,
            read=float(default_timeout),
            write=float(default_timeout),
            pool=5.0,
        )
        self._client = HttpClient(
            base_url=base_url, timeout=t, max_retries=2, backoff_factor=0.25
        )
        self.default_timeout = default_timeout

    # -------- SYNC request (used by ToolResult wrapper) --------
    def request_sync(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> httpx.Response:
        """Synchronous request used by the wrapper to avoid event-loop issues."""
        # If a base_url was provided to HttpClient, we can pass a relative url safely.
        _timeout = httpx.Timeout(
            connect=5.0,
            read=float(timeout or self.default_timeout),
            write=float(timeout or self.default_timeout),
            pool=5.0,
        )
        started = _now_ms()
        try:
            resp = self._client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                data=data,
                json_body=json_payload,
                timeout=_timeout,
            )
            ended = _now_ms()
            # Convert lightweight HttpResponse -> real httpx.Response for compatibility
            req = httpx.Request(method.upper(), resp.url)
            return httpx.Response(
                resp.status_code,
                content=(resp.text or "").encode("utf-8"),
                headers=resp.headers,
                request=req,
            )
        except (httpx.TimeoutException, httpx.ReadTimeout) as e:
            logger.error(
                "HTTP request timed out after %ss: %s %s | headers=%s params=%s",
                timeout or self.default_timeout,
                method.upper(),
                url,
                redact_for_log(headers or {}),
                redact_for_log(params or {}),
            )
            raise ToolExecutionError(
                f"HTTP request timed out after {timeout or self.default_timeout}s"
            ) from e
        except Exception as e:
            logger.error(
                "HTTP request failed: %s %s -> %s | headers=%s params=%s",
                method.upper(),
                url,
                str(e),
                redact_for_log(headers or {}),
                redact_for_log(params or {}),
            )
            raise ToolExecutionError(f"HTTP request failed: {e}") from e

    # -------- OPTIONAL ASYNC helper (for async callers outside ToolResult path) --------
    async def arequest(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> httpx.Response:
        """Async variant for agent code that wants awaitable responses (not used by wrapper)."""
        # Recreate an async httpx client via our HttpClient (already has an AsyncClient)
        _timeout = httpx.Timeout(
            connect=5.0,
            read=float(timeout or self.default_timeout),
            write=float(timeout or self.default_timeout),
            pool=5.0,
        )
        started = _now_ms()
        try:
            resp = await self._client.arequest(
                method=method,
                url=url,
                params=params,
                headers=headers,
                data=data,
                json_body=json_payload,
                timeout=_timeout,
            )
            req = httpx.Request(method.upper(), resp.url)
            return httpx.Response(
                resp.status_code,
                content=(resp.text or "").encode("utf-8"),
                headers=resp.headers,
                request=req,
            )
        except (httpx.TimeoutException, httpx.ReadTimeout) as e:
            logger.error(
                "HTTP request timed out after %ss: %s %s",
                timeout or self.default_timeout,
                method.upper(),
                url,
            )
            raise ToolExecutionError(
                f"HTTP request timed out after {timeout or self.default_timeout}s"
            ) from e
        except Exception as e:
            logger.error(
                "HTTP request failed: %s %s -> %s", method.upper(), url, str(e)
            )
            raise ToolExecutionError(f"HTTP request failed: {e}") from e

    # -------- ToolResult wrappers (SYNC by default) --------
    def request_result(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="http.request",
                args=redact_for_log(
                    {"method": method, "url": url, "headers": headers, "params": params}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] http.request",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )

        try:
            resp = self.request_sync(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                json_payload=json_payload,
                timeout=timeout,
            )
            meta = {
                "url": str(resp.request.url) if resp.request else url,
                "method": method,
                "status": resp.status_code,
            }
            if 200 <= resp.status_code < 400:
                return ToolResult.ok_result(
                    stdout=resp.text or "",
                    exit_code=0,
                    latency_ms=_now_ms() - start,
                    meta=meta,
                )
            else:
                return ToolResult.err_result(
                    error_type="Runtime",
                    stderr=(resp.text or ""),
                    latency_ms=_now_ms() - start,
                    meta=meta,
                )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta=redact_for_log(
                    {"url": url, "method": method, "headers": headers, "params": params}
                ),
            )
