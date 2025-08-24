# aegis/utils/http_client.py
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple, Union

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)


@dataclass
class HttpResponse:
    method: str
    url: str
    status_code: int
    headers: Dict[str, str]
    text: str
    duration_ms: int
    started_ms: int
    ended_ms: int

    def json(self) -> Any:
        """Best-effort JSON decode; returns None on failure."""
        try:
            return json.loads(self.text)
        except Exception:
            return None


def _now_ms() -> int:
    return int(time.time() * 1000)


def _redact_headers(
    headers: Mapping[str, str],
    sensitive_fields: Iterable[str],
) -> Dict[str, str]:
    sf = {k.lower() for k in sensitive_fields}
    return {k: ("******" if k.lower() in sf else v) for k, v in headers.items()}


class HttpClient:
    """
    A thin wrapper over httpx with:
      - sensible timeouts
      - bounded retries with backoff (idempotent methods by default)
      - response timing
      - header redaction helper for your logs (caller-owned logging)
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        backoff_factor: float = 0.2,
        verify: Union[bool, str] = True,
        headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff = backoff_factor
        self._headers = dict(headers or {})
        self._client = httpx.Client(
            base_url=base_url, timeout=timeout, verify=verify, headers=self._headers
        )
        self._aclient = httpx.AsyncClient(
            base_url=base_url, timeout=timeout, verify=verify, headers=self._headers
        )

    # ------------------------- Sync -------------------------

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        data: Optional[Union[bytes, str, Mapping[str, Any]]] = None,
        json_body: Optional[Any] = None,
        timeout: Optional[httpx.Timeout] = None,
        sensitive_headers: Iterable[str] = ("authorization", "x-api-key"),
        retry_on: Tuple[int, ...] = (408, 429, 500, 502, 503, 504),
    ) -> HttpResponse:
        started = _now_ms()
        merged_headers = dict(self._headers)
        if headers:
            merged_headers.update(headers)

        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._client.request(
                    method,
                    url,
                    params=params,
                    headers=merged_headers,
                    data=data,
                    json=json_body,
                    timeout=timeout or self._timeout,
                )
                if resp.status_code in retry_on and attempt < self._max_retries:
                    time.sleep(self._backoff * (2**attempt))
                    continue
                ended = _now_ms()
                return HttpResponse(
                    method=method.upper(),
                    url=str(resp.request.url),
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    text=resp.text,
                    duration_ms=ended - started,
                    started_ms=started,
                    ended_ms=ended,
                )
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.WriteError,
                httpx.RemoteProtocolError,
            ) as e:
                last_exc = e
                if attempt < self._max_retries:
                    time.sleep(self._backoff * (2**attempt))
                    continue
                raise
        # If we somehow exit the loop without returning/raising earlier:
        if last_exc:
            raise last_exc  # pragma: no cover

    # ------------------------- Async ------------------------

    async def arequest(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        data: Optional[Union[bytes, str, Mapping[str, Any]]] = None,
        json_body: Optional[Any] = None,
        timeout: Optional[httpx.Timeout] = None,
        sensitive_headers: Iterable[str] = ("authorization", "x-api-key"),
        retry_on: Tuple[int, ...] = (408, 429, 500, 502, 503, 504),
    ) -> HttpResponse:
        import asyncio

        started = _now_ms()
        merged_headers = dict(self._headers)
        if headers:
            merged_headers.update(headers)

        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._aclient.request(
                    method,
                    url,
                    params=params,
                    headers=merged_headers,
                    data=data,
                    json=json_body,
                    timeout=timeout or self._timeout,
                )
                if resp.status_code in retry_on and attempt < self._max_retries:
                    await asyncio.sleep(self._backoff * (2**attempt))
                    continue
                ended = _now_ms()
                return HttpResponse(
                    method=method.upper(),
                    url=str(resp.request.url),
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    text=resp.text,
                    duration_ms=ended - started,
                    started_ms=started,
                    ended_ms=ended,
                )
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.WriteError,
                httpx.RemoteProtocolError,
            ) as e:
                last_exc = e
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff * (2**attempt))
                    continue
                raise
        if last_exc:
            raise last_exc  # pragma: no cover

    # ------------------------- Utilities --------------------

    @staticmethod
    def redact_headers_for_log(
        headers: Mapping[str, str],
        sensitive_headers: Iterable[str] = ("authorization", "x-api-key"),
    ) -> Dict[str, str]:
        return _redact_headers(headers, sensitive_headers)

    # ------------------------- Cleanup ----------------------

    def close(self) -> None:
        self._client.close()

    async def aclose(self) -> None:
        await self._aclient.aclose()
