# aegis/tests/executors/test_redis_executor.py
"""
Unit tests for the RedisExecutor class.
"""
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError


@pytest.fixture
def mock_redis_client(monkeypatch):
    """Mocks the redis.Redis client class."""
    mock_client_instance = MagicMock()
    mock_redis_class = MagicMock(return_value=mock_client_instance)
    # Patch the class in the module where it's used
    monkeypatch.setattr("aegis.executors.redis.Redis", mock_redis_class)
    return mock_client_instance


@pytest.fixture
def mock_config_with_redis(monkeypatch):
    """Mocks get_config to return a config with a valid redis_url."""
    mock_get_config = MagicMock(
        return_value={"services": {"redis_url": "redis://localhost:6379/0"}}
    )
    monkeypatch.setattr("aegis.executors.redis.get_config", mock_get_config)


def test_redis_executor_init_success(mock_redis_client, mock_config_with_redis):
    """Verify the executor connects and pings on successful initialization."""
    from aegis.executors.redis_exec import RedisExecutor

    executor = RedisExecutor()
    assert executor.client is not None
    mock_redis_client.ping.assert_called_once()


def test_redis_executor_set_value(mock_redis_client, mock_config_with_redis):
    """Verify set_value calls the client's set method."""
    from aegis.executors.redis_exec import RedisExecutor

    executor = RedisExecutor()
    executor.set_value("my_key", "my_value")
    mock_redis_client.set.assert_called_once_with("my_key", "my_value")


def test_redis_executor_get_value(mock_redis_client, mock_config_with_redis):
    """Verify get_value calls the client's get method and returns the value."""
    mock_redis_client.get.return_value = "retrieved_value"
    from aegis.executors.redis_exec import RedisExecutor

    executor = RedisExecutor()
    result = executor.get_value("my_key")
    mock_redis_client.get.assert_called_once_with("my_key")
    assert result == "retrieved_value"


def test_redis_executor_get_value_not_found(mock_redis_client, mock_config_with_redis):
    """Verify get_value returns a 'not found' message if the key doesn't exist."""
    mock_redis_client.get.return_value = None
    from aegis.executors.redis_exec import RedisExecutor

    executor = RedisExecutor()
    result = executor.get_value("non_existent_key")
    assert "No value found" in result


def test_redis_executor_connection_fails(mock_redis_client, mock_config_with_redis):
    """Verify that methods raise ToolExecutionError if the client is not connected."""
    mock_redis_client.ping.side_effect = Exception("Connection refused")
    from aegis.executors.redis_exec import RedisExecutor

    executor = RedisExecutor()
    assert executor.client is None
    with pytest.raises(ToolExecutionError, match="Redis client is not connected"):
        executor.set_value("k", "v")
