# tests/executors/test_http_exec.py
import anyio
import httpx
import pytest

from aegis.executors.http_exec import HttpExecutor
from aegis.utils.http_client import HttpClient
from aegis.exceptions import ToolExecutionError


def _inject_mock_transport(
    monkeypatch, transport: httpx.MockTransport, *, max_retries: int = 2
):
    """
    Replace HttpClient's internal clients with instances backed by `transport`.
    This keeps the production code unchanged while letting us control I/O.
    """
    original_init = HttpClient.__init__

    def patched_init(
        self,
        *,
        base_url=None,
        timeout=None,
        max_retries=max_retries,
        backoff_factor=0.2,
        verify=True,
        headers=None
    ):
        # replicate attribute setup from real __init__
        self._timeout = timeout or httpx.Timeout(
            connect=5.0, read=30.0, write=30.0, pool=5.0
        )
        self._max_retries = max_retries
        self._backoff = backoff_factor
        self._headers = dict(headers or {})
        # inject mock transport for both sync and async clients
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
        # Close underlying clients without network effects
        await self._aclient.aclose()
        self._client.close()

    monkeypatch.setattr(HttpClient, "__init__", patched_init, raising=True)
    monkeypatch.setattr(HttpClient, "aclose", patched_aclose, raising=True)
    return original_init  # in case a future test wants to restore it


def test_http_executor_request_success_with_retry(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            # first call forces retry
            return httpx.Response(500, json={"retry": True})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    _inject_mock_transport(monkeypatch, transport, max_retries=2)

    execu = HttpExecutor(base_url="https://example.test", default_timeout=5)

    async def go():
        resp = await execu.request("GET", "/thing")
        # The override returns a shim with these attrs
        assert getattr(resp, "status_code", None) == 200
        assert "ok" in getattr(resp, "text", "")

    anyio.run(go)

    assert calls["n"] == 2  # one retry happened


def test_http_executor_request_raises_on_persistent_5xx(monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="nope")

    transport = httpx.MockTransport(handler)
    _inject_mock_transport(monkeypatch, transport, max_retries=1)

    execu = HttpExecutor(base_url="https://example.test", default_timeout=3)

    async def go():
        with pytest.raises(ToolExecutionError) as ei:
            await execu.request("GET", "/still-broken")
        # ensure error message carries status code context
        assert "HTTP 500" in str(ei.value) or "500" in str(ei.value)

    anyio.run(go)
