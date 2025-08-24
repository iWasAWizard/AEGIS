# tests/utils/test_http_client.py
import anyio
import httpx
import pytest
import types

from aegis.utils.http_client import HttpClient


def _no_sleep(*args, **kwargs):
    # backoff no-op for fast tests
    return None


async def _run(coro):
    return await coro


def test_arequest_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(502, text="bad gateway")
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    # Patch internal clients to use the mock transport
    orig_init = HttpClient.__init__

    def patched_init(
        self,
        *,
        base_url=None,
        timeout=None,
        max_retries=2,
        backoff_factor=0.0,
        verify=True,
        headers=None
    ):
        self._timeout = timeout or httpx.Timeout(
            connect=5.0, read=30.0, write=30.0, pool=5.0
        )
        self._max_retries = max_retries
        self._backoff = backoff_factor
        self._headers = dict(headers or {})
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
    monkeypatch.setattr(
        HttpClient, "_sleep", _no_sleep, raising=False
    )  # if implementation uses an internal sleep

    client = HttpClient(
        base_url="https://example.test", max_retries=2, backoff_factor=0.0
    )

    async def go():
        resp = await client.arequest("GET", "/ping")
        assert resp.status_code == 200
        assert "ok" in resp.text

    anyio.run(go)
    assert calls["n"] == 2  # one retry

    # restore, in case other tests rely on real __init__
    monkeypatch.setattr(HttpClient, "__init__", orig_init, raising=True)


def test_arequest_persistent_5xx_raises(monkeypatch):
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    transport = httpx.MockTransport(handler)

    def patched_init(
        self,
        *,
        base_url=None,
        timeout=None,
        max_retries=1,
        backoff_factor=0.0,
        verify=True,
        headers=None
    ):
        self._timeout = timeout or httpx.Timeout(
            connect=5.0, read=30.0, write=30.0, pool=5.0
        )
        self._max_retries = max_retries
        self._backoff = backoff_factor
        self._headers = dict(headers or {})
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
    monkeypatch.setattr(HttpClient, "_sleep", _no_sleep, raising=False)

    client = HttpClient(
        base_url="https://example.test", max_retries=1, backoff_factor=0.0
    )

    async def go():
        # Expect the client to raise after exhausting retries
        with pytest.raises(Exception) as ei:
            await client.arequest("GET", "/broken")
        assert "5" in str(ei.value) or "service unavailable" in str(ei.value).lower()

    anyio.run(go)
