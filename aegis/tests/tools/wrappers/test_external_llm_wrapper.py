# aegis/tests/tools/wrappers/test_llm_wrapper.py
"""
Unit tests for the external, third-party LLM wrapper tools (OpenAI).
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.external_llm import (
    llm_chat_openai,
    LLMChatInput,
)

# Mark openai as an optional dependency for testing
openai = pytest.importorskip("openai", reason="openai library not installed.")


# --- Fixtures ---


@pytest.fixture
def mock_openai_chat(monkeypatch):
    """Mocks the OpenAI ChatCompletion create method."""
    mock_create = MagicMock()
    # Simulate the response structure
    mock_choice = MagicMock()
    mock_choice.message = MagicMock()  # Ensure message attribute exists
    mock_choice.message.content = "Mocked OpenAI Response"

    mock_completion_response = MagicMock()
    mock_completion_response.choices = [mock_choice]
    mock_create.return_value = mock_completion_response

    # In recent versions, the client is instantiated. We patch the class method.
    # Patching openai.OpenAI().chat.completions.create
    mock_openai_instance = MagicMock()
    mock_openai_instance.chat.completions.create = mock_create

    # Patch the OpenAI class constructor to return our mock instance
    monkeypatch.setattr(openai, "OpenAI", MagicMock(return_value=mock_openai_instance))
    return mock_create


# --- Tests ---


def test_llm_chat_openai_success(mock_openai_chat):
    """Verify the tool correctly formats messages and calls the OpenAI client."""
    messages = [
        ChatMessage(role="system", content="You are a test assistant."),
        ChatMessage(role="user", content="Hello there."),
    ]
    input_data = LLMChatInput(
        messages=messages, model="gpt-4-test", temperature=0.5, api_key="test_key"
    )

    result = llm_chat_openai(input_data)

    # Check that OpenAI() was called with the api_key
    openai.OpenAI.assert_called_with(api_key="test_key")

    mock_openai_chat.assert_called_once()  # This mock_openai_chat is completions.create
    call_args = mock_openai_chat.call_args.kwargs

    assert call_args["model"] == "gpt-4-test"
    assert call_args["temperature"] == 0.5
    # Check that Pydantic models were correctly converted to dicts
    assert call_args["messages"] == [
        {"role": "system", "content": "You are a test assistant."},
        {"role": "user", "content": "Hello there."},
    ]
    assert result == "Mocked OpenAI Response"


def test_llm_chat_openai_api_error(mock_openai_chat):
    """Verify the tool handles exceptions from the OpenAI API."""
    # mock_openai_chat is completions.create
    mock_openai_chat.side_effect = openai.APIError(
        "API Error", response=MagicMock(), body=None
    )

    messages = [ChatMessage(role="user", content="This will fail.")]
    input_data = LLMChatInput(messages=messages)

    result = llm_chat_openai(input_data)
    assert "[ERROR] OpenAI chat completion failed" in result
    assert "API Error" in result
