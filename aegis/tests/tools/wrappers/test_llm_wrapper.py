# aegis/tests/tools/wrappers/test_llm_wrapper.py
"""
Unit tests for the external, third-party LLM wrapper tools.
"""
from unittest.mock import MagicMock

import pytest
import requests

# Mark openai as an optional dependency for testing
openai = pytest.importorskip("openai", reason="openai library not installed.")

from aegis.tools.wrappers.external_llm import (
    llm_chat_openai, LLMChatInput, ChatMessage,
    ollama_generate_direct, OllamaGenerateInput,
)


# --- Fixtures ---

@pytest.fixture
def mock_openai_chat(monkeypatch):
    """Mocks the OpenAI ChatCompletion create method."""
    mock_create = MagicMock()
    # Simulate the response structure
    mock_choice = MagicMock()
    mock_choice.message.content = "Mocked OpenAI Response"
    mock_create.return_value = MagicMock(choices=[mock_choice])

    # In recent versions, the client is instantiated. We patch the class method.
    monkeypatch.setattr(openai.resources.chat.Completions, "create", mock_create)
    return mock_create


@pytest.fixture
def mock_requests_post(monkeypatch):
    """Mocks requests.post for direct Ollama calls."""
    mock_post = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Mocked Ollama direct response"}
    mock_post.return_value = mock_response
    monkeypatch.setattr(requests, "post", mock_post)
    return mock_post


# --- Tests ---

def test_llm_chat_openai_success(mock_openai_chat):
    """Verify the tool correctly formats messages and calls the OpenAI client."""
    messages = [
        ChatMessage(role="system", content="You are a test assistant."),
        ChatMessage(role="user", content="Hello there."),
    ]
    input_data = LLMChatInput(messages=messages, model="gpt-4-test", temperature=0.5)

    result = llm_chat_openai(input_data)

    mock_openai_chat.assert_called_once()
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
    mock_openai_chat.side_effect = openai.APIError("API Error", response=MagicMock(), body=None)

    messages = [ChatMessage(role="user", content="This will fail.")]
    input_data = LLMChatInput(messages=messages)

    result = llm_chat_openai(input_data)
    assert "[ERROR] OpenAI chat completion failed" in result


def test_ollama_generate_direct_success(mock_requests_post):
    """Verify the tool constructs the correct payload for a direct Ollama call."""
    input_data = OllamaGenerateInput(
        model="codellama:latest",
        prompt="def hello():",
        system="You are a code completion model.",
        temperature=0.1
    )

    result = ollama_generate_direct(input_data)

    mock_requests_post.assert_called_once()
    call_args = mock_requests_post.call_args.kwargs

    assert call_args["url"] == "http://localhost:11434/api/generate"
    payload = call_args["json"]
    assert payload["model"] == "codellama:latest"
    assert payload["prompt"] == "def hello():"
    assert payload["system"] == "You are a code completion model."
    assert payload["temperature"] == 0.1
    assert result == "Mocked Ollama direct response"


def test_ollama_generate_direct_network_error(mock_requests_post):
    """Verify the tool handles network errors when calling Ollama."""
    mock_requests_post.side_effect = requests.RequestException("Network down")

    input_data = OllamaGenerateInput(model="test", prompt="test")
    result = ollama_generate_direct(input_data)

    assert "[ERROR] Ollama request failed" in result
