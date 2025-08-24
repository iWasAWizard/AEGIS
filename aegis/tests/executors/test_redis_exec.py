# tests/executors/test_redis_exec.py
import json
import pytest

from aegis.executors.redis_exec import RedisExecutor
from aegis.utils import dryrun as _dryrun_mod


def _mk_executor(monkeypatch):
    """
    Create a RedisExecutor without importing the real redis client or connecting anywhere.
    """

    def fake_init(self, *args, **kwargs):
        # no real client; wrappers directly call set_value/get_value/delete_value,
        # which we'll monkeypatch per-test
        self.default_timeout = 3

    monkeypatch.setattr(RedisExecutor, "__init__", fake_init, raising=True)
    return RedisExecutor()  # type: ignore[call-arg]


def test_set_value_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "set_value", lambda **kw: True, raising=True)

    res = exe.set_value_result(key="token", value="SECRET", expire_s=60)
    assert res.ok is True
    assert res.exit_code == 0
    # stdout is stringified return value
    assert res.stdout == "True"
    # ensure we didn't leak the actual value in meta
    assert res.meta.get("key") == "token"
    assert res.meta.get("expire_s") == 60


def test_get_value_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "get_value", lambda **kw: "v123", raising=True)

    res = exe.get_value_result(key="k1")
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout == "v123"
    assert res.meta.get("key") == "k1"


def test_delete_value_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "delete_value", lambda **kw: True, raising=True)

    res = exe.delete_value_result(key="k2")
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout == "True"
    assert res.meta.get("key") == "k2"


def test_error_mapping_timeout(monkeypatch):
    exe = _mk_executor(monkeypatch)

    class Timeouty(Exception):
        def __str__(self):
            return "request timeout to redis"

    def boom(**kw):
        raise Timeouty()

    monkeypatch.setattr(exe, "get_value", boom, raising=True)

    res = exe.get_value_result(key="slow")
    assert res.ok is False
    assert res.error_type == "Timeout"
    assert "timeout" in (res.stderr or "").lower()


def test_error_mapping_auth(monkeypatch):
    exe = _mk_executor(monkeypatch)

    def boom(**kw):
        raise RuntimeError("permission denied: bad auth")

    monkeypatch.setattr(exe, "set_value", boom, raising=True)

    res = exe.set_value_result(key="k", value="v")
    assert res.ok is False
    assert res.error_type == "Auth"
    assert "permission" in (res.stderr or "").lower()


def test_dry_run_paths(monkeypatch):
    exe = _mk_executor(monkeypatch)
    # Ensure dry-run is enabled and preview is deterministic for assertions
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", True, raising=False)
    monkeypatch.setattr(
        _dryrun_mod.dry_run,
        "preview_payload",
        lambda **kw: {"tool": kw.get("tool"), "args": kw.get("args")},
        raising=False,
    )

    r1 = exe.set_value_result(key="k", value="v", expire_s=None)
    r2 = exe.get_value_result(key="k")
    r3 = exe.delete_value_result(key="k")

    for r, tool in [(r1, "redis.set"), (r2, "redis.get"), (r3, "redis.del")]:
        assert r.ok is True
        assert r.stdout == "[DRY-RUN] " + tool
        assert r.meta and isinstance(r.meta.get("preview"), dict)
        assert r.meta["preview"].get("tool") == tool

    # Reset dry-run flag to avoid leaking to other tests
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", False, raising=False)
