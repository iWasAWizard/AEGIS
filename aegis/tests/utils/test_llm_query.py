# aegis/tests/utils/test_llm_query.py
"""
Unit tests for the core LLM query utility (now targeting KoboldCPP).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp  # Import aiohttp directly for ClientError
import pytest

from aegis.exceptions import PlannerError, ConfigurationError
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.llm_query import llm_query


@pytest.fixture
def mock_aiohttp_session_for_kobold(monkeypatch):
    """Mocks the aiohttp.ClientSession for controlled KoboldCPP responses."""
    mock_session_instance = MagicMock()
    mock_response = (
        AsyncMock()
    )  # Use AsyncMock for async methods like .json() and .text()

    # Configure __aenter__ to return the mock_response
    mock_post_context_manager = AsyncMock()
    mock_post_context_manager.__aenter__.return_value = mock_response

    mock_session_instance.post.return_value = (
        mock_post_context_manager  # post() returns the async context manager
    )

    mock_session_class = MagicMock(return_value=mock_session_instance)
    monkeypatch.setattr(
        "aegis.utils.llm_query.aiohttp.ClientSession", mock_session_class
    )
    return (
        mock_response  # Return the mock_response for configuring its behavior in tests
    )


@pytest.fixture
def sample_runtime_config() -> RuntimeExecutionConfig:
    """Provides a sample RuntimeExecutionConfig for tests."""
    return RuntimeExecutionConfig(
        koboldcpp_api_url="http://test-kobold:5001/api/v1/generate",
        llm_model_name="test-model-hint",  # For prompt_formatter hint
        temperature=0.1,
        max_context_length=1024,
        max_tokens_to_generate=128,
        llm_planning_timeout=10,
    )


@pytest.mark.asyncio
async def test_llm_query_kobold_success(
    mock_aiohttp_session_for_kobold, sample_runtime_config
):
    """Verify a successful query to KoboldCPP returns the model's response content."""
    mock_aiohttp_session_for_kobold.ok = True
    mock_aiohttp_session_for_kobold.json.return_value = {
        "results": [{"text": "KoboldCPP says hello"}]
    }

    result = await llm_query("system prompt", "user prompt", sample_runtime_config)
    assert result == "KoboldCPP says hello"

    # Verify the post call was made to the correct URL from runtime_config
    session_instance = aiohttp.ClientSession.return_value
    session_instance.post.assert_called_once()
    call_args_list = session_instance.post.call_args_list
    assert len(call_args_list) == 1
    args, kwargs = call_args_list[0]
    assert args[0] == sample_runtime_config.koboldcpp_api_url  # Check URL

    # Check some key parts of the payload
    payload = kwargs["json"]
    assert payload["prompt"] is not None  # Formatted prompt should be there
    assert payload["temperature"] == sample_runtime_config.temperature
    assert payload["max_context_length"] == sample_runtime_config.max_context_length
    assert payload["max_length"] == sample_runtime_config.max_tokens_to_generate


@pytest.mark.asyncio
async def test_llm_query_kobold_http_error(
    mock_aiohttp_session_for_kobold, sample_runtime_config
):
    """Verify that an HTTP error from KoboldCPP raises a PlannerError."""
    mock_aiohttp_session_for_kobold.ok = False
    mock_aiohttp_session_for_kobold.status = 500
    mock_aiohttp_session_for_kobold.text.return_value = (
        "Kobold Internal Server Error"  # .text() is async
    )

    with pytest.raises(PlannerError, match="Failed to query LLM Backend. Status: 500"):
        await llm_query("system", "user", sample_runtime_config)


@pytest.mark.asyncio
@patch(
    "aegis.utils.llm_query.aiohttp.ClientSession.post"
)  # Patch at the source of the call
async def test_llm_query_kobold_timeout_error(mock_post_method, sample_runtime_config):
    """Verify that a client timeout during KoboldCPP query raises a PlannerError."""
    mock_post_method.side_effect = asyncio.TimeoutError

    with pytest.raises(PlannerError, match="LLM query timed out"):
        await llm_query("system", "user", sample_runtime_config)


@pytest.mark.asyncio
async def test_llm_query_kobold_missing_results_field(
    mock_aiohttp_session_for_kobold, sample_runtime_config
):
    """Verify a malformed JSON (missing 'results') from KoboldCPP raises a PlannerError."""
    mock_aiohttp_session_for_kobold.ok = True
    mock_aiohttp_session_for_kobold.json.return_value = {
        "error": "malformed_no_results"
    }

    with pytest.raises(
        PlannerError,
        match="Invalid LLM Backend response format: 'results' key is malformed.",
    ):
        await llm_query("system", "user", sample_runtime_config)


@pytest.mark.asyncio
async def test_llm_query_kobold_empty_results_list(
    mock_aiohttp_session_for_kobold, sample_runtime_config
):
    """Verify a malformed JSON (empty 'results' list) from KoboldCPP raises a PlannerError."""
    mock_aiohttp_session_for_kobold.ok = True
    mock_aiohttp_session_for_kobold.json.return_value = {"results": []}

    with pytest.raises(
        PlannerError,
        match="Invalid LLM Backend response format: 'results' key is malformed.",
    ):
        await llm_query("system", "user", sample_runtime_config)


@pytest.mark.asyncio
async def test_llm_query_kobold_missing_text_field(
    mock_aiohttp_session_for_kobold, sample_runtime_config
):
    """Verify a malformed JSON (missing 'text' in results[0]) from KoboldCPP raises a PlannerError."""
    mock_aiohttp_session_for_kobold.ok = True
    mock_aiohttp_session_for_kobold.json.return_value = {
        "results": [{"not_text": "something"}]
    }

    with pytest.raises(
        PlannerError,
        match="Invalid LLM Backend response format: 'text' key missing in results",
    ):
        await llm_query("system", "user", sample_runtime_config)


@pytest.mark.asyncio
async def test_llm_query_kobold_client_error(
    mock_aiohttp_session_for_kobold, sample_runtime_config
):
    """Verify that a generic aiohttp.ClientError raises a PlannerError."""
    # To simulate ClientError on session.post(), we make the __aenter__ raise it.
    # The session.post() call itself returns an async context manager.
    session_instance = aiohttp.ClientSession.return_value
    session_instance.post.return_value.__aenter__.side_effect = aiohttp.ClientError(
        "Generic network issue"
    )

    with pytest.raises(
        PlannerError, match="Network error during LLM query: Generic network issue"
    ):
        await llm_query("system", "user", sample_runtime_config)


@pytest.mark.asyncio
async def test_llm_query_no_kobold_url(sample_runtime_config):
    """Verify ConfigurationError if koboldcpp_api_url is not set."""
    sample_runtime_config.koboldcpp_api_url = None
    with pytest.raises(
        ConfigurationError, match="KoboldCPP backend: koboldcpp_api_url not configured."
    ):
        await llm_query("system", "user", sample_runtime_config)
