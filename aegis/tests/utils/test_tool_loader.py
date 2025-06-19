# aegis/tests/utils/test_tool_loader.py
"""
Unit tests for the dynamic tool loader utility.
"""
import sys
from pathlib import Path

import pytest

from aegis.registry import TOOL_REGISTRY
from aegis.utils.tool_loader import import_all_tools


@pytest.fixture(autouse=True)
def clean_registry():
    """Fixture to ensure the registry is clean before each test."""
    original_registry = TOOL_REGISTRY.copy()
    TOOL_REGISTRY.clear()
    yield
    TOOL_REGISTRY.clear()
    TOOL_REGISTRY.update(original_registry)


@pytest.fixture
def plugin_setup(tmp_path: Path):
    """Creates a temporary plugins directory with various test plugin files."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "__init__.py").touch()

    # 1. A valid plugin
    valid_plugin_content = """
from pydantic import BaseModel
from aegis.registry import register_tool

class MyValidPluginInput(BaseModel):
    pass

@register_tool(name="my_valid_plugin", input_model=MyValidPluginInput, tags=[], description="")
def my_valid_plugin_func(_: MyValidPluginInput):
    return "valid"
"""
    (plugins_dir / "valid_plugin.py").write_text(valid_plugin_content)

    # 2. A plugin with a syntax error
    broken_plugin_content = """
def broken_function(:
    pass
"""
    (plugins_dir / "broken_plugin.py").write_text(broken_plugin_content)

    # 3. An empty plugin file
    (plugins_dir / "empty_plugin.py").touch()

    # Temporarily add the project root to the path for importing
    original_path = sys.path[:]
    sys.path.insert(0, str(tmp_path))

    yield

    # Clean up the path
    sys.path = original_path


def test_load_core_and_plugin_tools(plugin_setup, monkeypatch):
    """Verify that the loader imports core tools and valid plugin tools."""
    # We need to mock the Path object to point to our temp directory
    # for the plugins, but let the core tools load normally.

    # The loader's logic is relative to its own path, so we can let
    # the core tool loading proceed as is. We only need to ensure
    # the CWD is set for the plugin discovery part.

    # We will clear the registry, then run the loader.
    TOOL_REGISTRY.clear()

    # Mock the project root to point to our temp path
    monkeypatch.setattr(Path, "cwd", lambda: Path.cwd())  # Ensure cwd is correct

    import_all_tools()

    # Check that a known core tool is registered
    assert "run_local_command" in TOOL_REGISTRY

    # Check that our valid plugin tool is registered
    assert "my_valid_plugin" in TOOL_REGISTRY
    assert TOOL_REGISTRY["my_valid_plugin"].description == ""


def test_loader_handles_broken_plugin(plugin_setup, caplog):
    """Verify the loader logs an error for a broken plugin but doesn't crash."""
    TOOL_REGISTRY.clear()

    import_all_tools()

    # The valid plugin should still be loaded
    assert "my_valid_plugin" in TOOL_REGISTRY

    # The broken plugin should not be in the registry
    assert "broken_plugin" not in TOOL_REGISTRY

    # Check that an error was logged for the broken file
    assert "Failed to import tool module" in caplog.text
    assert "plugins.broken_plugin" in caplog.text
    assert "SyntaxError" in caplog.text
