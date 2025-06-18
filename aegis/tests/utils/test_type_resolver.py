# aegis/tests/utils/test_type_resolver.py
"""
Unit tests for the dynamic type resolver utility.
"""
import pytest

from aegis.agents.task_state import TaskState
from aegis.exceptions import ConfigurationError
from aegis.utils.type_resolver import resolve_dotted_type


def test_resolve_dotted_type_success():
    """Verify that a valid dotted path returns the correct class object."""
    dotted_path = "aegis.schemas.task_state.TaskState"
    resolved_class = resolve_dotted_type(dotted_path)

    assert resolved_class is TaskState


def test_resolve_dotted_type_module_not_found():
    """Verify that a non-existent module raises a ConfigurationError."""
    dotted_path = "aegis.non_existent_module.SomeClass"

    with pytest.raises(ConfigurationError, match="Unable to resolve type"):
        resolve_dotted_type(dotted_path)


def test_resolve_dotted_type_class_not_found():
    """Verify that a non-existent class in a valid module raises a ConfigurationError."""
    dotted_path = "aegis.schemas.task_state.NonExistentClass"

    with pytest.raises(ConfigurationError, match="Unable to resolve type"):
        resolve_dotted_type(dotted_path)


def test_resolve_dotted_type_invalid_path():
    """Verify that a malformed path raises a ConfigurationError."""
    dotted_path = "InvalidPathWithNoDots"

    with pytest.raises(ConfigurationError, match="Invalid dotted path format"):
        resolve_dotted_type(dotted_path)
