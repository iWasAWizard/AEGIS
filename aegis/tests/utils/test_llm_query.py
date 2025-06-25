# aegis/tests/utils/test_llm_query.py
"""
Unit tests for the core LLM query utility.
"""
from unittest.mock import AsyncMock, patch

import pytest

from aegis.exceptions import PlannerError, ConfigurationError
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.llm_query import llm_query, get_provider_for_profile


@pytest.fixture
def mock_get_provider(monkeypatch):
    """Mocks the get_provider_for_profile factory function."""
    mock_provider_instance = AsyncMock()
    mock_provider_instance.get_completion.return_value = "mocked completion"
    
    mock_factory = patch('aegis.utils.llm_query.get_provider_for_profile', return_value=mock_provider_instance).start()
    
    yield mock_factory, mock_provider_instance
    
    patch.stopall()


@pytest.fixture
def sample_runtime_config() -> RuntimeExecutionConfig:
    """Provides a sample RuntimeExecutionConfig for tests."""
    return RuntimeExecutionConfig(backend_profile="test_profile")


@pytest.mark.asyncio
async def test_llm_query_success(mock_get_provider, sample_runtime_config):
    """Verify a successful query dispatches to the correct provider and returns its result."""
    mock_factory, mock_provider = mock_get_provider
    
    result = await llm_query("system prompt", "user prompt", sample_runtime_config)
    
    # Check that the factory was called with the correct profile
    mock_factory.assert_called_once_with("test_profile")
    
    # Check that the provider's get_completion method was called
    mock_provider.get_completion.assert_awaited_once()
    
    # Verify the arguments passed to get_completion
    args, kwargs = mock_provider.get_completion.call_args
    messages_arg = args[0]
    runtime_config_arg = args[1]
    
    assert messages_arg == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]
    assert runtime_config_arg == sample_runtime_config
    
    # Check the final result
    assert result == "mocked completion"


@pytest.mark.asyncio
async def test_llm_query_provider_raises_planner_error(mock_get_provider, sample_runtime_config):
    """Verify that a PlannerError from the provider is propagated correctly."""
    mock_factory, mock_provider = mock_get_provider
    mock_provider.get_completion.side_effect = PlannerError("Provider-level failure")
    
    with pytest.raises(PlannerError, match="Provider-level failure"):
        await llm_query("system", "user", sample_runtime_config)


@pytest.mark.asyncio
async def test_llm_query_factory_raises_config_error(sample_runtime_config):
    """Verify that a ConfigurationError from the factory is propagated."""
    with patch('aegis.utils.llm_query.get_provider_for_profile', side_effect=ConfigurationError("Bad profile")):
        with pytest.raises(ConfigurationError, match="Bad profile"):
            await llm_query("system", "user", sample_runtime_config)