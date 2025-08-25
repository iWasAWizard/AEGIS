# tests/tools/test_redis_wrapper.py
import types
import importlib

import pytest

from aegis.registry import reset_registry_for_tests, get_tool


@pytest.fixture(autouse=True)
def _fresh_registry(monkeypatch):
    reset_registry_for_tests()
    yield
    reset_registry_for_tests()


def _register_and_patch_redis(monkeypatch):
    # Import the wrappers to register tools
    mod = importlib.import_module("aegis.tools.wrappers.redis")

    # Patch the RedisExecutor symbol *inside* the wrappers module
    class FakeRedis:
        def __init__(self, *a, **kw):
            pass

        def ping_result(self):
            from aegis.schemas.tool_result import ToolResult

            return ToolResult.ok_result(stdout="PONG", exit_code=0, latency_ms=1)

        def get_result(self, key):
            from aegis.schemas.tool_result import ToolResult

            return ToolResult.ok_result(
                stdout="", exit_code=0, latency_ms=1, meta={"key": key, "miss": True}
            )

        def set_result(self, key, value, **kw):
            from aegis.schemas.tool_result import ToolResult

            return ToolResult.ok_result(
                stdout="OK", exit_code=0, latency_ms=1, meta={"key": key}
            )

        def delete_result(self, *keys):
            from aegis.schemas.tool_result import ToolResult

            return ToolResult.ok_result(
                stdout=str(len(keys)), exit_code=0, latency_ms=1
            )

        def keys_result(self, pattern="*"):
            from aegis.schemas.tool_result import ToolResult

            return ToolResult.ok_result(stdout='["a","b"]', exit_code=0, latency_ms=1)

        def hgetall_result(self, key):
            from aegis.schemas.tool_result import ToolResult

            return ToolResult.ok_result(stdout='{"x":"1"}', exit_code=0, latency_ms=1)

        def expire_result(self, key, seconds):
            from aegis.schemas.tool_result import ToolResult

            return ToolResult.ok_result(stdout="OK", exit_code=0, latency_ms=1)

        def eval_result(self, script, keys=None, args=None):
            from aegis.schemas.tool_result import ToolResult

            return ToolResult.ok_result(stdout='{"rc":0}', exit_code=0, latency_ms=1)

    monkeypatch.setattr(mod, "RedisExecutor", FakeRedis, raising=True)
    return mod


def test_redis_ping(monkeypatch):
    _register_and_patch_redis(monkeypatch)
    entry = get_tool("redis.ping")
    model = entry.input_model()  # no fields required
    res = entry.func(input_data=model)
    assert res.success is True
    assert (res.stdout or "").strip() == "PONG"


def test_redis_get_miss(monkeypatch):
    _register_and_patch_redis(monkeypatch)
    entry = get_tool("redis.get")
    model = entry.input_model(key="nope")
    res = entry.func(input_data=model)
    assert res.success is True
    assert res.stdout == ""  # miss
    assert res.meta and res.meta.get("miss") is True


def test_redis_set_ok(monkeypatch):
    _register_and_patch_redis(monkeypatch)
    entry = get_tool("redis.set")
    model = entry.input_model(key="k", value="v")
    res = entry.func(input_data=model)
    assert res.success is True
    assert (res.stdout or "").strip() == "OK"


def test_redis_delete_count(monkeypatch):
    _register_and_patch_redis(monkeypatch)
    entry = get_tool("redis.delete")
    model = entry.input_model(keys=["a", "b", "c"])
    res = entry.func(input_data=model)
    assert res.success is True
    assert res.stdout == "3"
