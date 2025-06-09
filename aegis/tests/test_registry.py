# aegis/tests/test_registry.py
"""
Tests for the tool registration and lookup system.
"""
import pytest
from pydantic import BaseModel

from aegis.exceptions import ToolNotFoundError, ToolValidationError
from aegis.registry import TOOL_REGISTRY
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


# A global variable to hold the original tool so we can re-register it
_original_safe_tool = None


@pytest.fixture(autouse=True)
def clean_registry():
    """Fixture to ensure the registry is clean before and after each test."""
    global _original_safe_tool

    if "test_safe_tool" in TOOL_REGISTRY:
        _original_safe_tool = TOOL_REGISTRY["test_safe_tool"]

    TOOL_REGISTRY.pop("test_safe_tool", None)
    TOOL_REGISTRY.pop("test_unsafe_tool", None)

    @register_tool(name="test_safe_tool", input_model=SafeToolInput, tags=[], description="")
    def safe_tool_func(_: SafeToolInput):
        return "safe"

    @register_tool(name="test_unsafe_tool", input_model=UnsafeToolInput, tags=[], description="", safe_mode=False)
    def unsafe_tool_func(_: UnsafeToolInput):
        return "unsafe"

    yield

    TOOL_REGISTRY.pop("test_safe_tool", None)
    TOOL_REGISTRY.pop("test_unsafe_tool", None)

    if _original_safe_tool:
        TOOL_REGISTRY["test_safe_tool"] = _original_safe_tool


def test_get_tool_success():
    """Verify that a registered tool can be retrieved."""
    tool = get_tool("test_safe_tool")
    assert tool is not None
    assert isinstance(tool, ToolEntry)
    assert tool.name == "test_safe_tool"


def test_get_tool_not_found():
    """Verify that get_tool raises ToolNotFoundError for a non-existent tool."""
    with pytest.raises(ToolNotFoundError, match="not found in registry"):
        get_tool("non_existent_tool")


def test_get_tool_safe_mode_blocking():
    """Verify that safe_mode=True blocks retrieval of unsafe tools."""
    with pytest.raises(ToolNotFoundError, match="blocked by safe mode"):
        get_tool("test_unsafe_tool")


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
        @register_tool(name="test_safe_tool", input_model=SafeToolInput, tags=[], description="")
        def duplicate_tool_func(_: SafeToolInput):
            pass


def test_registration_with_invalid_model_fails():
    """Verify that the registry rejects tools with non-Pydantic input models."""

    class NotAPydanticModel:
        pass

    with pytest.raises(ToolValidationError, match="Input model must be a subclass of pydantic.BaseModel"):
        validate_input_model(NotAPydanticModel)
