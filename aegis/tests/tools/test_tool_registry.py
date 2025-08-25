# tests/tools/test_tool_registry.py
import types
import textwrap

import pytest
from pydantic import BaseModel

from aegis.registry import (
    ToolEntry,
    register_tool,
    tool,
    get_tool,
    list_tools,
    ensure_discovered,
    reset_registry_for_tests,
)
from aegis.exceptions import ToolNotFoundError


class _EchoIn(BaseModel):
    msg: str


def _echo_impl(*, input_data: _EchoIn):
    return {"echo": input_data.msg}


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry_for_tests()
    yield
    reset_registry_for_tests()


def test_register_and_get_tool():
    entry = ToolEntry(name="test.echo", input_model=_EchoIn, func=_echo_impl, timeout=5)
    register_tool(entry)
    got = get_tool("test.echo")
    assert got.name == "test.echo"
    assert got.input_model is _EchoIn
    assert got.func is _echo_impl
    assert got.timeout == 5


def test_idempotent_registration_same_signature():
    entry = ToolEntry(name="test.echo", input_model=_EchoIn, func=_echo_impl, timeout=5)
    register_tool(entry)
    register_tool(entry)  # no-op
    tools = list(list_tools())
    assert len([t for t in tools if t.name == "test.echo"]) == 1


def test_reregister_different_impl_replaces():
    def impl_a(*, input_data: _EchoIn):
        return {"a": input_data.msg}

    def impl_b(*, input_data: _EchoIn):
        return {"b": input_data.msg}

    register_tool(ToolEntry("test.echo", _EchoIn, impl_a, timeout=1))
    register_tool(ToolEntry("test.echo", _EchoIn, impl_b, timeout=2))
    got = get_tool("test.echo")
    assert got.func is impl_b
    assert got.timeout == 2


def test_decorator_registers_function():
    @tool("decor.echo", _EchoIn, timeout=3)
    def f(*, input_data: _EchoIn):
        return {"ok": True}

    got = get_tool("decor.echo")
    assert got.func is f
    assert got.timeout == 3
    assert got.input_model is _EchoIn


def test_missing_tool_raises():
    with pytest.raises(ToolNotFoundError):
        get_tool("nope.missing")


def test_ensure_discovered_calls_importer_once(monkeypatch):
    calls = {"n": 0}

    def importer():
        calls["n"] += 1
        register_tool(ToolEntry("x", _EchoIn, _echo_impl, timeout=None))

    ensure_discovered(importer)
    ensure_discovered(importer)
    assert calls["n"] == 1  # only once
    assert get_tool("x").name == "x"
