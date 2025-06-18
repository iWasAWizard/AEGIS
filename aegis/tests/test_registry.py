# aegis/tests/test_registry.py
"""
Tests for the tool registration and lookup system.
"""
import pytest
from pydantic import BaseModel
import logging

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


_original_safe_tool_entry_for_overwrite_test = None


@pytest.fixture(autouse=True)
def clean_registry_and_setup_base_tools():
    """Fixture to ensure the registry is clean and base tools are set up."""
    global _original_safe_tool_entry_for_overwrite_test

    TOOL_REGISTRY.clear()

    @register_tool(
        name="test_safe_tool",
        input_model=SafeToolInput,
        tags=["safe"],
        description="A safe test tool.",
    )
    def safe_tool_func(_: SafeToolInput):
        return "safe_tool_output"

    _original_safe_tool_entry_for_overwrite_test = TOOL_REGISTRY["test_safe_tool"]

    @register_tool(
        name="test_unsafe_tool",
        input_model=UnsafeToolInput,
        tags=["unsafe"],
        description="An unsafe test tool.",
        safe_mode=False,
    )
    def unsafe_tool_func(_: UnsafeToolInput):
        return "unsafe_tool_output"

    yield

    TOOL_REGISTRY.clear()
    _original_safe_tool_entry_for_overwrite_test = None


def test_get_tool_success():
    """Verify that a registered tool can be retrieved."""
    tool = get_tool("test_safe_tool")
    assert tool is not None
    assert isinstance(tool, ToolEntry)
    assert tool.name == "test_safe_tool"


def test_get_tool_not_found():
    """Verify that get_tool raises ToolNotFoundError for a non-existent tool."""
    with pytest.raises(ToolNotFoundError, match="not found in registry. Available:"):
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


def test_duplicate_registration_warns_and_overwrites(caplog):
    """Verify that registering a tool with a duplicate name logs a warning and overwrites."""

    original_tool_function = TOOL_REGISTRY["test_safe_tool"].run

    with caplog.at_level(logging.WARNING):

        @register_tool(
            name="test_safe_tool",
            input_model=SafeToolInput,
            tags=["overwritten"],
            description="Overwritten tool.",
        )
        def new_duplicate_tool_func(_: SafeToolInput):
            return "overwritten_output"

    assert (
        "A tool with the name 'test_safe_tool' is already registered. Overwriting."
        in caplog.text
    )

    overwritten_tool_entry = TOOL_REGISTRY["test_safe_tool"]
    assert overwritten_tool_entry.description == "Overwritten tool."
    assert "overwritten" in overwritten_tool_entry.tags
    assert overwritten_tool_entry.run is not original_tool_function
    assert overwritten_tool_entry.run(SafeToolInput()) == "overwritten_output"


def test_registration_with_invalid_model_fails():
    """Verify that the registry rejects tools with non-Pydantic input models."""

    class NotAPydanticModel:
        pass

    with pytest.raises(
        ToolValidationError,
        match="Input model must be a subclass of pydantic.BaseModel",
    ):
        validate_input_model(NotAPydanticModel)  # type: ignore
