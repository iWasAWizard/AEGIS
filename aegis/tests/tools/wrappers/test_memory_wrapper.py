# aegis/tests/tools/wrappers/test_memory_wrapper.py
"""
Unit tests for the long-term memory wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.memory import (
    save_to_memory,
    SaveToMemoryInput,
    recall_from_memory,
    RecallFromMemoryInput,
)


@pytest.fixture
def mock_redis_executor(monkeypatch):
    """Mocks the RedisExecutor methods."""
    mock = MagicMock()
    mock.set_value.return_value = "Value successfully set for key 'test_key'."
    mock.get_value.return_value = "recalled_value"

    # Patch the class in the module where it's used
    monkeypatch.setattr(
        "aegis.tools.wrappers.memory.RedisExecutor", lambda *args, **kwargs: mock
    )
    return mock


def test_save_to_memory_success(mock_redis_executor):
    """Verify save_to_memory calls the executor's set_value method."""
    input_data = SaveToMemoryInput(key="test_key", value="test_value")
    result = save_to_memory(input_data)

    mock_redis_executor.set_value.assert_called_once_with("test_key", "test_value")
    assert result == "Value successfully set for key 'test_key'."


def test_save_to_memory_executor_fails(mock_redis_executor):
    """Verify ToolExecutionError is raised if the executor fails."""
    mock_redis_executor.set_value.side_effect = Exception("Redis connection failed")
    input_data = SaveToMemoryInput(key="test_key", value="test_value")

    with pytest.raises(ToolExecutionError, match="Failed to save to memory"):
        save_to_memory(input_data)


def test_recall_from_memory_success(mock_redis_executor):
    """Verify recall_from_memory calls the executor's get_value method."""
    input_data = RecallFromMemoryInput(key="test_key")
    result = recall_from_memory(input_data)

    mock_redis_executor.get_value.assert_called_once_with("test_key")
    assert result == "recalled_value"


def test_recall_from_memory_executor_fails(mock_redis_executor):
    """Verify ToolExecutionError is raised if the executor fails."""
    mock_redis_executor.get_value.side_effect = Exception("Redis connection failed")
    input_data = RecallFromMemoryInput(key="test_key")

    with pytest.raises(ToolExecutionError, match="Failed to recall from memory"):
        recall_from_memory(input_data)
