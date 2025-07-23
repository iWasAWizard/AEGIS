# aegis/tests/tools/wrappers/test_agentic_wrapper.py
"""
Unit tests for the agent-as-a-tool wrapper.
"""
from unittest.mock import MagicMock

import pytest
import requests

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.agentic import (
    dispatch_subtask_to_agent,
    DispatchSubtaskInput,
)


@pytest.fixture
def mock_requests_post(monkeypatch):
    """Mocks the requests.post call."""
    mock = MagicMock()
    monkeypatch.setattr(requests, "post", mock)
    return mock


def test_dispatch_subtask_to_agent_success(mock_requests_post):
    """Verify the tool correctly calls the launch API and returns the summary."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"summary": "Sub-agent completed successfully."}
    mock_requests_post.return_value = mock_response

    input_data = DispatchSubtaskInput(
        prompt="Perform a sub-task.",
        preset="default",
        backend_profile="test_backend",
    )

    result = dispatch_subtask_to_agent(input_data)

    mock_requests_post.assert_called_once()
    call_kwargs = mock_requests_post.call_args.kwargs
    assert call_kwargs["url"] == "http://localhost:8000/api/launch"
    assert call_kwargs["json"]["task"]["prompt"] == "Perform a sub-task."
    assert call_kwargs["json"]["config"] == "default"
    assert call_kwargs["json"]["execution"]["backend_profile"] == "test_backend"

    assert result == "Sub-agent completed successfully."


def test_dispatch_subtask_to_agent_http_error(mock_requests_post):
    """Verify that an HTTPError from the API call is raised as a ToolExecutionError."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"detail": "Sub-agent failed."}
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )
    mock_requests_post.return_value = mock_response

    input_data = DispatchSubtaskInput(
        prompt="This will fail.", preset="default", backend_profile="test_backend"
    )

    with pytest.raises(ToolExecutionError, match="Sub-agent task failed: Sub-agent failed."):
        dispatch_subtask_to_agent(input_data)


def test_dispatch_subtask_to_agent_network_error(mock_requests_post):
    """Verify a network error is raised as a ToolExecutionError."""
    mock_requests_post.side_effect = requests.exceptions.ConnectionError(
        "Could not connect."
    )

    input_data = DispatchSubtaskInput(
        prompt="This will fail.", preset="default", backend_profile="test_backend"
    )

    with pytest.raises(
        ToolExecutionError, match="Could not dispatch sub-task due to a network error"
    ):
        dispatch_subtask_to_agent(input_data)