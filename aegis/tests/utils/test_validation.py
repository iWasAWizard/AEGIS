# aegis/tests/utils/test_validation.py
"""
Tests for the configuration validation utilities.
"""
import pytest

from aegis.utils.validation import validate_node_names


def test_validate_node_names_success():
    """Verify a valid configuration passes validation."""
    valid_config = {
        "entrypoint": "start",
        "nodes": [
            {"id": "start", "tool": "tool1"},
            {"id": "end", "tool": "tool2"},
        ],
        "edges": [("start", "end")],
        "condition_node": "end",
        "condition_map": {"__end__": "__end__"},
    }
    # Should not raise any exception
    validate_node_names(valid_config)


def test_validate_node_names_bad_entrypoint():
    """Verify a non-existent entrypoint raises a ValueError."""
    config = {
        "entrypoint": "non_existent_start",
        "nodes": [{"id": "plan", "tool": "tool1"}],
    }
    with pytest.raises(
        ValueError, match="Unknown node name in config: 'non_existent_start'"
    ):
        validate_node_names(config)


def test_validate_node_names_bad_edge():
    """Verify an edge pointing to a non-existent node raises a ValueError."""
    config = {
        "entrypoint": "start",
        "nodes": [{"id": "start", "tool": "tool1"}],
        "edges": [("start", "non_existent_end")],
    }
    with pytest.raises(
        ValueError, match="Unknown node name in config: 'non_existent_end'"
    ):
        validate_node_names(config)


def test_validate_node_names_bad_condition_map():
    """Verify a condition map pointing to a non-existent node raises a ValueError."""
    config = {
        "entrypoint": "start",
        "nodes": [{"id": "start", "tool": "tool1"}],
        "condition_node": "start",
        "condition_map": {"next": "non_existent_node"},
    }
    with pytest.raises(
        ValueError, match="Unknown node name in config: 'non_existent_node'"
    ):
        validate_node_names(config)
