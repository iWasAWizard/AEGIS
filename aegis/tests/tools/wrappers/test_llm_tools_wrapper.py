# aegis/tests/tools/wrappers/test_llm_tools_wrapper.py
"""
Unit tests for the high-level, LLM-based wrapper tools.
"""
from unittest.mock import AsyncMock

import pytest

from aegis.tools.wrappers.generative_tools import (
    invoke_llm_query, LLMQueryInput,
    summarize_text, TextContentInput,
    rewrite_for_readability,
    extract_action_items,
    explain_code, CodeContentInput,
    generate_tests_for_code,
)


# --- Fixture ---

@pytest.fixture
def mock_llm_query(monkeypatch):
    """Mocks the core llm_query utility."""
    mock = AsyncMock(return_value="Mocked LLM Response")
    # Patch the function in the module where it is imported and used
    monkeypatch.setattr("aegis.tools.wrappers.llm_query.llm_query", mock)
    return mock


# --- Tests ---

@pytest.mark.asyncio
async def test_invoke_llm_query(mock_llm_query):
    """Verify the generic invoke tool passes prompts correctly."""
    input_data = LLMQueryInput(
        user_prompt="User question",
        system_prompt="Custom system instruction"
    )
    await invoke_llm_query(input_data)

    mock_llm_query.assert_awaited_once_with(
        system_prompt="Custom system instruction",
        user_prompt="User question"
    )


@pytest.mark.asyncio
async def test_summarize_text(mock_llm_query):
    """Verify summarize_text uses the correct system prompt."""
    input_data = TextContentInput(text="This is a long document...")
    await summarize_text(input_data)

    mock_llm_query.assert_awaited_once()
    call_args = mock_llm_query.call_args.kwargs
    assert "expert summarizer" in call_args["system_prompt"]
    assert call_args["user_prompt"] == "This is a long document..."


@pytest.mark.asyncio
async def test_rewrite_for_readability(mock_llm_query):
    """Verify rewrite_for_readability uses the correct system prompt."""
    input_data = TextContentInput(text="some dense text")
    await rewrite_for_readability(input_data)

    mock_llm_query.assert_awaited_once()
    call_args = mock_llm_query.call_args.kwargs
    assert "expert technical writer" in call_args["system_prompt"]
    assert "Please rewrite this:" in call_args["user_prompt"]


@pytest.mark.asyncio
async def test_extract_action_items(mock_llm_query):
    """Verify extract_action_items uses the correct system prompt."""
    input_data = TextContentInput(text="A meeting transcript.")
    await extract_action_items(input_data)

    mock_llm_query.assert_awaited_once()
    call_args = mock_llm_query.call_args.kwargs
    assert "identifying action items" in call_args["system_prompt"]
    assert "Extract action items from this:" in call_args["user_prompt"]


@pytest.mark.asyncio
async def test_explain_code(mock_llm_query):
    """Verify explain_code uses the correct system prompt."""
    input_data = CodeContentInput(code="def f(x): return x+1")
    await explain_code(input_data)

    mock_llm_query.assert_awaited_once()
    call_args = mock_llm_query.call_args.kwargs
    assert "expert code reviewer" in call_args["system_prompt"]
    assert "Explain this code:" in call_args["user_prompt"]
    assert "def f(x): return x+1" in call_args["user_prompt"]


@pytest.mark.asyncio
async def test_generate_tests_for_code(mock_llm_query):
    """Verify generate_tests_for_code uses the correct system prompt for pytest."""
    input_data = CodeContentInput(code="def f(x): return x")
    await generate_tests_for_code(input_data)

    mock_llm_query.assert_awaited_once()
    call_args = mock_llm_query.call_args.kwargs
    assert "senior software engineer" in call_args["system_prompt"]
    assert "`pytest` framework" in call_args["system_prompt"]
    assert "Write pytest unit tests for this code:" in call_args["user_prompt"]
