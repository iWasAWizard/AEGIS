# aegis/tests/tools/wrappers/test_data_wrapper.py
"""
Unit tests for the data wrapper tools.
"""
from unittest.mock import MagicMock, patch

import pytest

from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolExecutionError
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.tools.wrappers.data import (
    extract_structured_data,
    ExtractStructuredDataInput,
    diff_text_blocks,
    DiffTextBlocksInput,
)


@pytest.fixture
def mock_instructor_client(monkeypatch):
    """Mocks the instructor-patched OpenAI client."""
    mock_client_instance = MagicMock()
    mock_create = MagicMock()
    mock_client_instance.chat.completions.create = mock_create

    mock_patch = MagicMock(return_value=mock_client_instance)
    monkeypatch.setattr("aegis.tools.wrappers.data.instructor.patch", mock_patch)
    monkeypatch.setattr("aegis.tools.wrappers.data.OpenAI", MagicMock())
    return mock_create


@pytest.fixture
def mock_backend_loader(monkeypatch):
    """Mocks the backend configuration loader."""
    mock_config = {
        "llm_url": "http://mock-backend/v1/chat/completions",
        "model": "mock-model",
    }
    mock_get_config = MagicMock(return_value=MagicMock(**mock_config))
    monkeypatch.setattr("aegis.tools.wrappers.data.get_backend_config", mock_get_config)


def test_extract_structured_data_success(mock_instructor_client, mock_backend_loader):
    """Verify the tool correctly uses instructor to extract data."""
    # The mocked `create` method should return an object with a `model_dump` method
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {"name": "John Doe", "age": 30}
    mock_instructor_client.return_value = mock_response

    schema = {
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }
    input_data = ExtractStructuredDataInput(
        text_to_parse="The user is John Doe, aged 30.", extraction_schema=schema
    )
    state = TaskState(
        task_id="t1",
        task_prompt="p",
        runtime=RuntimeExecutionConfig(backend_profile="test_backend"),
    )

    result = extract_structured_data(input_data, state)

    assert result == {"name": "John Doe", "age": 30}
    mock_instructor_client.assert_called_once()


def test_extract_structured_data_instructor_fails(
    mock_instructor_client, mock_backend_loader
):
    """Verify a failure during the LLM call is raised as a ToolExecutionError."""
    mock_instructor_client.side_effect = Exception("LLM call failed")
    schema = {"properties": {"name": {"type": "string"}}}
    input_data = ExtractStructuredDataInput(
        text_to_parse="text", extraction_schema=schema
    )
    state = TaskState(
        task_id="t1",
        task_prompt="p",
        runtime=RuntimeExecutionConfig(backend_profile="test_backend"),
    )

    with pytest.raises(ToolExecutionError, match="LLM data extraction failed"):
        extract_structured_data(input_data, state)


def test_diff_text_blocks():
    """Verify the diff tool produces a correct unified diff."""
    old_text = "line1\nline2\nline3"
    new_text = "line1\nline TWO\nline3"
    input_data = DiffTextBlocksInput(old=old_text, new=new_text)

    result = diff_text_blocks(input_data)

    assert "-line2" in result
    assert "+line TWO" in result
    assert " line1" in result
