# aegis/tests/test_llm_query.py
"""
Tests for the llm_query utility, focusing on error handling and formatting.
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import ClientResponseError

from aegis.utils.llm_query import llm_query


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_llm_query_success(mock_post):
    """Verify a successful query returns the model's response content."""
    # Mock the async context manager for the response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = asyncio.Future()
    mock_response.json.return_value.set_result({"response": "LLM says hello"})

    # The __aenter__ of the mock_post context manager should return our mock_response
    mock_post.return_value.__aenter__.return_value = mock_response

    result = await llm_query("system prompt", "user prompt")
    assert result == "LLM says hello"


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_llm_query_http_error(mock_post):
    """Verify that an HTTP error from the server raises a RuntimeError."""
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text.return_value = asyncio.Future()
    mock_response.text.return_value.set_result("Internal Server Error")

    # Raise a ClientResponseError when the response is handled
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=500,
        message="Server Error",
    )
    mock_post.return_value.__aenter__.return_value = mock_response

    with pytest.raises(RuntimeError, match="Failed to query Ollama"):
        await llm_query("system", "user")


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_llm_query_timeout_error(mock_post):
    """Verify that a client timeout raises a RuntimeError."""
    mock_post.side_effect = asyncio.TimeoutError

    with pytest.raises(RuntimeError, match="LLM query timed out"):
        await llm_query("system", "user")


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_llm_query_missing_response_field(mock_post):
    """Verify a malformed JSON response from the LLM raises a RuntimeError."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = asyncio.Future()
    # Return a dict that's missing the 'response' key
    mock_response.json.return_value.set_result({"error": "malformed"})
    mock_post.return_value.__aenter__.return_value = mock_response

    with pytest.raises(RuntimeError, match="Invalid Ollama response format"):
        await llm_query("system", "user")
