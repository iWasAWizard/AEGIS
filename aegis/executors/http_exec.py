# aegis/executors/http_exec.py
"""
Provides a client for making HTTP requests.
"""
from typing import Optional, Dict, Any

import httpx
from aegis.utils.http_client import HttpClient

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time

logger = setup_logger(__name__)


class HttpExecutor:
    """A client for making HTTP requests consistently."""

    def __init__(self, base_url: Optional[str] = None, default_timeout: int = 30):
        """
        Initialize the HTTP executor.

        :param base_url: Optional base URL to resolve relative paths.
        :type base_url: Optional[str]
        :param default_timeout: Default timeout for all requests.
        :type default_timeout: int
        """
        self.base_url = base_url
        self.default_timeout = default_timeout

    async def request(
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
        """
        Perform an HTTP request using httpx.

        :param method: HTTP method (GET, POST, etc.).
        :type method: str
        :param url: The request URL (absolute or relative to base_url).
        :type url: str
        :param headers: Optional HTTP headers.
        :type headers: Optional[Dict[str, str]]
        :param params: Optional URL query parameters.
        :type params: Optional[Dict[str, Any]]
        :param data: Optional raw request body (e.g., for form data or plain text).
        :type data: Optional[str | bytes]
        :param json_payload: Optional dictionary to send as JSON payload.
                             If provided, 'Content-Type: application/json' is set automatically
                             unless already in headers. 'data' should be None if this is used.
        :type json_payload: Optional[Dict[str, Any]]
        :param timeout: Optional timeout for this specific request.
        :type timeout: Optional[int]
        :return: The `httpx.Response` object.
        :rtype: httpx.Response
        :raises ToolExecutionError: If the HTTP operation fails (network error, timeout, etc.)
        """
        eff_timeout = timeout or self.default_timeout
        target_url = (
            url
            if (url.startswith("http://") or url.startswith("https://"))
            else (
                (self.base_url.rstrip("/") + "/" + url.lstrip("/"))
                if self.base_url
                else url
            )
        )

        # Use the shared HttpClient under the hood; return an httpx.Response to keep API stable.
        client = HttpClient(
            base_url=None,  # we pass a fully-resolved URL below
            timeout=httpx.Timeout(
                connect=5.0, read=float(eff_timeout), write=float(eff_timeout), pool=5.0
            ),
            max_retries=2,
            backoff_factor=0.25,
            verify=True,
            headers=headers or {},
        )

        try:
            resp = await client.arequest(
                method=method,
                url=target_url,
                params=params,
                headers=headers,
                data=data,
                json_body=json_payload,
                timeout=None,  # per-request timeout already set on the client above
            )
            # Build a real httpx.Response so upstream code relying on .status_code/.text continues to work.
            req = httpx.Request(method.upper(), resp.url)
            return httpx.Response(
                resp.status_code,
                content=(resp.text or "").encode("utf-8"),
                headers=resp.headers,
                request=req,
            )
        except httpx.TimeoutException as e:
            logger.error(
                "HTTP request timed out after %ss: %s %s | headers=%s params=%s",
                eff_timeout,
                method.upper(),
                target_url,
                redact_for_log(headers or {}),
                redact_for_log(params or {}),
            )
            raise ToolExecutionError(
                f"HTTP request timed out after {eff_timeout}s"
            ) from e
        except Exception as e:
            logger.error(
                "HTTP request failed: %s %s -> %s | headers=%s params=%s",
                method.upper(),
                target_url,
                str(e),
                redact_for_log(headers or {}),
                redact_for_log(params or {}),
            )
            raise ToolExecutionError(f"HTTP request failed: {str(e)}") from e
        finally:
            try:
                await client.aclose()
            except Exception:
                pass


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


class HttpExecutorToolResultMixin:
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
            # Note: original request is async; for sync wrapper, you may call within an event loop.
            # If your call sites are async, prefer awaiting `request()` directly and wrap outside.
            import anyio

            async def _go(self):
                resp = await self.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    data=data,
                    json_payload=json_payload,
                    timeout=timeout,
                )
                return resp

            resp = anyio.run(lambda: _go(self))  # lightweight bridge
            meta = {
                "status_code": getattr(resp, "status_code", None),
                "url": url,
                "method": method,
            }
            return ToolResult.ok_result(
                stdout=getattr(resp, "text", None),
                exit_code=0,
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


HttpExecutor.request_result = HttpExecutorToolResultMixin.request_result
