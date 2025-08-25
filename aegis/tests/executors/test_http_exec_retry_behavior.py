# tests/executors/test_http_exec_retry_behavior.py
"""
HTTP executor retry/raising behavior tests.

Covers:
- GET retries on 5xx and succeeds on second attempt
- GET raises ToolExecutionError on persistent 5xx/429/408 after retries
- POST does not retry (single call) and raises on 5xx
- Timeout exceptions are mapped to ToolExecutionError
"""
from __future__ import annotations

import asyncio
import httpx
import anyio
import pytest

from aegis.executors.http_exec import HttpExecutor
from aegis.utils.http_client import HttpClient
from aegis.exceptions import ToolExecutionError


def _inject_mock_transport(
    monkeypatch,
    transport: httpx.MockTransport,
    *,
    max_retries: int = 2,
    backoff_factor: float = 0.25,
):
    """
    Replace HttpClient's internal clients with instances backed by `transport`.
    Avoids network calls while letting us use the real executor logic.
    """
    original_init = HttpClient.__init__

    def patched_init(
        self,
        *,
        base_url=None,
        timeout=None,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        verify=True,
        headers=None,
    ):
        # mirror the real attribute setup
        self._timeout = timeout or httpx.Timeout(
            connect=5.0, read=30.0, write=30.0, pool=5.0
        )
        self._max_retries = max_retries
        self._backoff = backoff_factor
        self._headers = dict(headers or {})
        # inject the mock transport for both sync and async clients
        self._client = httpx.Client(
            base_url=base_url,
            timeout=self._timeout,
            verify=verify,
            headers=self._headers,
            transport=transport,
        )
        self._aclient = httpx.AsyncClient(
            base_url=base_url,
            timeout=self._timeout,
            verify=verify,
            headers=self._headers,
            transport=transport,
        )

    async def patched_aclose(self):
        await self._aclient.aclose()
        self._client.close()

    monkeypatch.setattr(HttpClient, "__init__", patched_init, raising=True)
    monkeypatch.setattr(HttpClient, "aclose", patched_aclose, raising=True)
    return original_init


def _speed_up_sleep(monkeypatch):
    # avoid real backoff delays in retry loops
    monkeypatch.setattr(
        asyncio, "sleep", lambda *_args, **_kw: anyio.sleep(0), raising=False
    )
    import time as _time

    monkeypatch.setattr(_time, "sleep", lambda *_: None, raising=False)


def test_get_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="first fails")
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    _inject_mock_transport(monkeypatch, transport, max_retries=2)
    _speed_up_sleep(monkeypatch)

    exe = HttpExecutor(base_url="https://example.test", default_timeout=5)

    async def go():
        resp = await exe.request("GET", "/ping")
        assert resp.status_code == 200
        assert "ok" in resp.text

    anyio.run(go)
    # one retry happened
    assert calls["n"] == 2


@pytest.mark.parametrize("status", [500, 502, 503, 504, 429, 408])
def test_get_persistent_error_raises(monkeypatch, status):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=f"still {status}")

    transport = httpx.MockTransport(handler)
    _inject_mock_transport(monkeypatch, transport, max_retries=2)
    _speed_up_sleep(monkeypatch)

    exe = HttpExecutor(base_url="https://example.test", default_timeout=3)

    async def go():
        with pytest.raises(ToolExecutionError) as ei:
            await exe.request("GET", "/flaky")
        msg = str(ei.value)
        assert str(status) in msg

    anyio.run(go)


def test_post_does_not_retry(monkeypatch):
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, text="nope")

    transport = httpx.MockTransport(handler)
    _inject_mock_transport(monkeypatch, transport, max_retries=5)
    _speed_up_sleep(monkeypatch)

    exe = HttpExecutor(base_url="https://example.test", default_timeout=3)

    async def go():
        with pytest.raises(ToolExecutionError):
            await exe.request("POST", "/submit", json_payload={"x": 1})

    anyio.run(go)
    # no retries for non-idempotent POST
    assert calls["n"] == 1


def test_timeout_is_mapped_to_toolerror(monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        # Simulate a transport-level read timeout raised by httpx
        raise httpx.ReadTimeout("read timed out")

    transport = httpx.MockTransport(handler)
    _inject_mock_transport(monkeypatch, transport, max_retries=1)
    _speed_up_sleep(monkeypatch)

    exe = HttpExecutor(base_url="https://example.test", default_timeout=1)

    async def go():
        with pytest.raises(ToolExecutionError) as ei:
            await exe.request("GET", "/slow")
        assert "timed out" in str(ei.value).lower()

    anyio.run(go)
