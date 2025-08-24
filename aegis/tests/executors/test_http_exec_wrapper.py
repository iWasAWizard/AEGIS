# tests/executors/test_http_exec_wrapper.py
import pytest

from aegis.executors.http_exec import HttpExecutor
from aegis.utils import dryrun as _dryrun_mod


class FakeResp:
    def __init__(self, status_code=200, text="ok", url="https://example.com/x"):
        self.status_code = status_code
        self.text = text
        self.url = url


def _mk_executor():
    # Use default config; we'll stub the async request method per-test.
    return HttpExecutor(base_url=None, default_timeout=1)


def test_request_result_success(monkeypatch):
    exe = _mk_executor()

    async def fake_request(method, url, **kwargs):
        return FakeResp(status_code=201, text="created", url=url)

    monkeypatch.setattr(exe, "request", fake_request, raising=True)

    res = exe.request_result(
        method="POST",
        url="https://api.example.com/items",
        headers={"Authorization": "Bearer SECRET"},
        json_payload={"x": 1},
        timeout=2,
    )
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout == "created"
    assert res.meta.get("status_code") == 201
    assert res.meta.get("method") == "POST"
    assert res.meta.get("url") == "https://api.example.com/items"


def test_request_result_timeout_mapping(monkeypatch):
    exe = _mk_executor()

    class Timeouty(Exception):
        def __str__(self):
            return "request timeout while contacting server"

    async def boom(*a, **k):
        raise Timeouty()

    monkeypatch.setattr(exe, "request", boom, raising=True)

    res = exe.request_result(method="GET", url="https://slow.example.com")
    assert res.ok is False
    assert res.error_type == "Timeout"
    assert "timeout" in (res.stderr or "").lower()


def test_request_result_auth_mapping(monkeypatch):
    exe = _mk_executor()

    async def boom(*a, **k):
        raise RuntimeError("permission denied: token invalid")

    monkeypatch.setattr(exe, "request", boom, raising=True)

    res = exe.request_result(method="GET", url="https://api.example.com/private")
    assert res.ok is False
    assert res.error_type == "Auth"
    assert "permission" in (res.stderr or "").lower()


def test_request_result_dry_run(monkeypatch):
    exe = _mk_executor()
    # Enable DRY-RUN and make preview predictable
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", True, raising=False)
    monkeypatch.setattr(
        _dryrun_mod.dry_run,
        "preview_payload",
        lambda **kw: {"tool": kw.get("tool"), "args": kw.get("args")},
        raising=False,
    )

    res = exe.request_result(
        method="GET",
        url="https://api.example.com/ping",
        headers={"X-Api-Key": "SECRET"},
        params={"q": "x"},
    )
    assert res.ok is True
    assert res.stdout == "[DRY-RUN] http.request"
    assert isinstance(res.meta.get("preview"), dict)
    assert res.meta["preview"]["tool"] == "http.request"

    # Reset dry-run flag for other tests
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", False, raising=False)
