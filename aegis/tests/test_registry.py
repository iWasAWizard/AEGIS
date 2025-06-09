# aegis/tests/test_registry.py
"""
Tests for the tool registration and lookup system.
"""
import pytest
from pydantic import BaseModel

from aegis.registry import (
    ToolEntry,
    get_tool,
    list_tools,
    register_tool,
    validate_input_model,
)


class SafeToolInput(BaseModel):
    pass


class UnsafeToolInput(BaseModel):
    pass


@register_tool(
    name="test_safe_tool", input_model=SafeToolInput, tags=[], description=""
)
def safe_tool_func(_: SafeToolInput):
    return "safe"


@register_tool(
    name="test_unsafe_tool",
    input_model=UnsafeToolInput,
    tags=[],
    description="",
    safe_mode=False,
)
def unsafe_tool_func(_: UnsafeToolInput):
    return "unsafe"


def test_get_tool_success():
    """Verify that a registered tool can be retrieved."""
    tool = get_tool("test_safe_tool")
    assert tool is not None
    assert isinstance(tool, ToolEntry)
    assert tool.name == "test_safe_tool"


def test_get_tool_not_found():
    """Verify that get_tool returns None for a non-existent tool."""
    tool = get_tool("non_existent_tool")
    assert tool is None


def test_get_tool_safe_mode_blocking():
    """Verify that safe_mode=True blocks retrieval of unsafe tools."""
    tool = get_tool("test_unsafe_tool")
    assert tool is None, "Should not retrieve unsafe tool when safe_mode is on"


def test_get_tool_safe_mode_allowed():
    """Verify that safe_mode=False allows retrieval of unsafe tools."""
    tool = get_tool("test_unsafe_tool", safe_mode=False)
    assert tool is not None
    assert tool.name == "test_unsafe_tool"


def test_list_tools_safe_mode():
    """Verify that list_tools only returns safe tools by default."""
    tools = list_tools()
    assert "test_safe_tool" in tools
    assert "test_unsafe_tool" not in tools


def test_list_tools_unsafe_mode():
    """Verify that list_tools returns all tools when safe_mode is off."""
    tools = list_tools(safe_mode=False)
    assert "test_safe_tool" in tools
    assert "test_unsafe_tool" in tools


def test_duplicate_registration_fails():
    """Verify that registering a tool with a duplicate name raises an error."""
    with pytest.raises(ValueError, match="is already registered"):

        @register_tool(
            name="test_safe_tool", input_model=SafeToolInput, tags=[], description=""
        )
        def duplicate_tool_func(_: SafeToolInput):
            pass


def test_registration_with_invalid_model_fails():
    """Verify that the registry rejects tools with non-Pydantic input models."""

    class NotAPydanticModel:
        pass

    with pytest.raises(TypeError, match="invalid or non-instantiable"):
        validate_input_model(NotAPydanticModel)
