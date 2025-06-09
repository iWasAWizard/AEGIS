# aegis/tests/utils/test_llm_query.py
"""
Unit tests for the core LLM query utility.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from aegis.exceptions import PlannerError
from aegis.utils.llm_query import llm_query


@pytest.fixture
def mock_aiohttp_session(monkeypatch):
    """Mocks the aiohttp.ClientSession for controlled responses."""
    mock_session_instance = MagicMock()
    # This makes 'async with session.post(...) as response:' work
    mock_response = AsyncMock()
    mock_session_instance.post.return_value = mock_response
    mock_session_instance.post.return_value.__aenter__.return_value = mock_response

    mock_session_class = MagicMock(return_value=mock_session_instance)
    monkeypatch.setattr("aegis.utils.llm_query.aiohttp.ClientSession", mock_session_class)
    return mock_response


@pytest.mark.asyncio
async def test_llm_query_success(mock_aiohttp_session):
    """Verify a successful query returns the model's response content."""
    mock_aiohttp_session.ok = True
    mock_aiohttp_session.json.return_value = {"response": "LLM says hello"}

    result = await llm_query("system prompt", "user prompt")
    assert result == "LLM says hello"


@pytest.mark.asyncio
async def test_llm_query_http_error(mock_aiohttp_session):
    """Verify that an HTTP error from the server raises a PlannerError."""
    mock_aiohttp_session.ok = False
    mock_aiohttp_session.status = 500
    mock_aiohttp_session.text.return_value = "Internal Server Error"

    with pytest.raises(PlannerError, match="Failed to query Ollama"):
        await llm_query("system", "user")


@pytest.mark.asyncio
@patch("aegis.utils.llm_query.aiohttp.ClientSession.post")
async def test_llm_query_timeout_error(mock_post):
    """Verify that a client timeout raises a PlannerError."""
    mock_post.side_effect = asyncio.TimeoutError

    with pytest.raises(PlannerError, match="LLM query timed out"):
        await llm_query("system", "user")


@pytest.mark.asyncio
async def test_llm_query_missing_response_field(mock_aiohttp_session):
    """Verify a malformed JSON response from the LLM raises a PlannerError."""
    mock_aiohttp_session.ok = True
    mock_aiohttp_session.json.return_value = {"error": "malformed"}

    with pytest.raises(PlannerError, match="Invalid Ollama response format"):
        await llm_query("system", "user")
