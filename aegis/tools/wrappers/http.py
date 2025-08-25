# aegis/tools/wrappers/http.py
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Literal
from pydantic import BaseModel, Field

from aegis.registry import tool
from aegis.schemas.tool_result import ToolResult
from aegis.executors.http_exec import HttpExecutor


# ---------- Input models ----------


class _HttpBase(BaseModel):
    # Optional base URL; if provided and `url` is relative, it will be joined.
    base_url: Optional[str] = Field(default=None, description="Optional base URL")
    url: str = Field(..., description="Path or full URL")
    headers: Optional[Mapping[str, str]] = None
    params: Optional[Mapping[str, Any]] = None
    timeout: Optional[int] = Field(
        default=None, description="Per-request timeout (seconds)"
    )


class HttpRequestInput(_HttpBase):
    method: Literal["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"]
    data: Optional[Any] = Field(default=None, description="Raw/form data body")
    json_body: Optional[Any] = Field(default=None, description="JSON body")


class HttpGetInput(_HttpBase):
    pass


class HttpPostInput(_HttpBase):
    data: Optional[Any] = None
    json_body: Optional[Any] = None


class HttpPutInput(HttpPostInput):
    pass


class HttpDeleteInput(_HttpBase):
    pass


class HttpHeadInput(_HttpBase):
    pass


# ---------- Tool shims ----------


def _exec(
    *,
    method: str,
    base_url: Optional[str],
    url: str,
    headers: Optional[Mapping[str, str]],
    params: Optional[Mapping[str, Any]],
    data: Optional[Any],
    json_body: Optional[Any],
    timeout: Optional[int],
) -> ToolResult:
    ex = HttpExecutor(base_url=base_url, default_timeout=timeout or 30)
    # Use the ToolResult-producing wrapper on the executor
    return ex.request_result(
        method=method,
        url=url,
        headers=dict(headers or {}),
        params=dict(params or {}),
        data=data,
        json_payload=json_body,
        timeout=timeout,
    )


@tool("http.request", HttpRequestInput, timeout=120)
def http_request(*, input_data: HttpRequestInput) -> ToolResult:
    """Generic HTTP request with method, headers/params, data or json."""
    return _exec(
        method=input_data.method,
        base_url=input_data.base_url,
        url=input_data.url,
        headers=input_data.headers,
        params=input_data.params,
        data=input_data.data,
        json_body=input_data.json_body,
        timeout=input_data.timeout,
    )


@tool("http.get", HttpGetInput, timeout=60)
def http_get(*, input_data: HttpGetInput) -> ToolResult:
    """HTTP GET convenience wrapper."""
    return _exec(
        method="GET",
        base_url=input_data.base_url,
        url=input_data.url,
        headers=input_data.headers,
        params=input_data.params,
        data=None,
        json_body=None,
        timeout=input_data.timeout,
    )


@tool("http.post", HttpPostInput, timeout=120)
def http_post(*, input_data: HttpPostInput) -> ToolResult:
    """HTTP POST convenience wrapper."""
    return _exec(
        method="POST",
        base_url=input_data.base_url,
        url=input_data.url,
        headers=input_data.headers,
        params=input_data.params,
        data=input_data.data,
        json_body=input_data.json_body,
        timeout=input_data.timeout,
    )


@tool("http.put", HttpPutInput, timeout=120)
def http_put(*, input_data: HttpPutInput) -> ToolResult:
    """HTTP PUT convenience wrapper."""
    return _exec(
        method="PUT",
        base_url=input_data.base_url,
        url=input_data.url,
        headers=input_data.headers,
        params=input_data.params,
        data=input_data.data,
        json_body=input_data.json_body,
        timeout=input_data.timeout,
    )


@tool("http.delete", HttpDeleteInput, timeout=60)
def http_delete(*, input_data: HttpDeleteInput) -> ToolResult:
    """HTTP DELETE convenience wrapper."""
    return _exec(
        method="DELETE",
        base_url=input_data.base_url,
        url=input_data.url,
        headers=input_data.headers,
        params=input_data.params,
        data=None,
        json_body=None,
        timeout=input_data.timeout,
    )


@tool("http.head", HttpHeadInput, timeout=30)
def http_head(*, input_data: HttpHeadInput) -> ToolResult:
    """HTTP HEAD convenience wrapper."""
    return _exec(
        method="HEAD",
        base_url=input_data.base_url,
        url=input_data.url,
        headers=input_data.headers,
        params=input_data.params,
        data=None,
        json_body=None,
        timeout=input_data.timeout,
    )
