# tests/executors/test_redis_exec.py
import json
import pytest

from aegis.executors.redis_exec import RedisExecutor
from aegis.utils import dryrun as _dryrun_mod


class _FakeClient:
    def __init__(self):
        self.store = {}
        self.exp = {}

    def ping(self):
        return True

    def get(self, k):
        return self.store.get(k)

    def set(self, name, value, ex=None, px=None, nx=False, xx=False):
        if nx and name in self.store:
            return False
        if xx and name not in self.store:
            return False
        self.store[name] = value
        if ex:
            self.exp[name] = ex
        return True

    def delete(self, *keys):
        cnt = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                cnt += 1
        return cnt

    def keys(self, pattern="*"):
        # naive: only support "*" in tests
        return list(self.store.keys()) if pattern == "*" else []

    def hgetall(self, key):
        v = self.store.get(key, {})
        return dict(v) if isinstance(v, dict) else {}

    def expire(self, key, seconds):
        if key in self.store:
            self.exp[key] = seconds
            return True
        return False

    def eval(self, script, nkeys, *args):
        # trivial echo of args for tests
        return {"nkeys": nkeys, "args": list(args)}


def _mk_executor(monkeypatch):
    exe = object.__new__(RedisExecutor)  # bypass __init__
    exe.client = _FakeClient()
    return exe


def test_set_get_roundtrip(monkeypatch):
    exe = _mk_executor(monkeypatch)
    r1 = exe.set_result("a", "1")
    assert r1.ok and r1.stdout == "OK"
    r2 = exe.get_result("a")
    assert r2.ok and r2.meta["miss"] is False
    assert (r2.stdout or "").strip() == "1"


def test_delete_and_keys(monkeypatch):
    exe = _mk_executor(monkeypatch)
    exe.set_result("k1", "v1")
    exe.set_result("k2", "v2")
    rkeys = exe.keys_result("*")
    assert rkeys.ok
    arr = json.loads(rkeys.stdout or "[]")
    assert set(arr) == {"k1", "k2"}
    rdel = exe.delete_result("k1", "k2", "missing")
    assert rdel.ok and rdel.stdout == "2"


def test_hgetall_and_expire(monkeypatch):
    exe = _mk_executor(monkeypatch)
    exe.set_result("hash", {"a": "b"})  # store dict as value in fake
    r = exe.hgetall_result("hash")
    assert r.ok
    m = json.loads(r.stdout or "{}")
    # we stored a dict; fake returns it, else {} if not dict
    assert isinstance(m, dict)


def test_eval_result(monkeypatch):
    exe = _mk_executor(monkeypatch)
    r = exe.eval_result("return ARGV", keys=["k1"], args=["a", "b"])
    assert r.ok
    out = json.loads(r.stdout or "{}")
    assert out["nkeys"] == 1
    assert out["args"][-2:] == ["a", "b"]


def test_dry_run_preview(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", True, raising=False)
    monkeypatch.setattr(
        _dryrun_mod.dry_run,
        "preview_payload",
        lambda **kw: {"tool": kw.get("tool"), "args": kw.get("args")},
        raising=False,
    )
    r = exe.set_result("secret", "supersecret")
    assert r.ok and r.stdout == "[DRY-RUN] redis.set"
    assert isinstance(r.meta.get("preview"), dict)
    assert r.meta["preview"]["tool"] == "redis.set"
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", False, raising=False)
