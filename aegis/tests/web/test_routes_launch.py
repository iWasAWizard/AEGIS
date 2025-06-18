# aegis/tests/web/test_routes_launch.py
"""
Unit tests for the main task launching API route.
"""
from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from aegis.exceptions import ConfigurationError, PlannerError
from aegis.schemas.agent import AgentConfig
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.serve_dashboard import app

client = TestClient(app)


# --- Fixtures ---


@pytest.fixture
def mock_load_agent_config(monkeypatch):
    """Mocks the load_agent_config utility."""
    mock = MagicMock(
        return_value=AgentConfig(
            state_type=MagicMock(), entrypoint="test", runtime=RuntimeExecutionConfig()
        )
    )
    monkeypatch.setattr("aegis.web.routes_launch.load_agent_config", mock)
    return mock


@pytest.fixture
def mock_agent_graph(monkeypatch):
    """Mocks the AgentGraph class and its methods."""
    mock_ainvoke = AsyncMock()
    mock_graph_instance = MagicMock()
    mock_graph_instance.ainvoke = mock_ainvoke

    mock_graph_class = MagicMock()
    mock_graph_class.return_value.build_graph.return_value = mock_graph_instance

    monkeypatch.setattr("aegis.web.routes_launch.AgentGraph", mock_graph_class)
    return mock_ainvoke


# --- Tests ---


def test_launch_task_success(mock_load_agent_config, mock_agent_graph):
    """Test a successful task launch from a valid payload."""
    final_state_summary = {
        "final_summary": "Task completed successfully.",
        "history": [],
    }
    mock_agent_graph.return_value = final_state_summary

    payload = {"task": {"prompt": "Test a successful launch"}, "config": "default"}

    response = client.post("/api/launch", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["summary"] == "Task completed successfully."
    mock_load_agent_config.assert_called_once()
    mock_agent_graph.assert_awaited_once()


def test_launch_task_config_error(mock_load_agent_config):
    """Test that a ConfigurationError returns a 400 Bad Request."""
    mock_load_agent_config.side_effect = ConfigurationError("Invalid preset name")

    payload = {"task": {"prompt": "This will fail loading"}, "config": "bad_preset"}

    response = client.post("/api/launch", json=payload)

    assert response.status_code == 400
    assert "Invalid Configuration" in response.json()["detail"]
    assert "Invalid preset name" in response.json()["detail"]


def test_launch_task_planner_error(mock_load_agent_config, mock_agent_graph):
    """Test that a PlannerError during agent execution returns a 500 Internal Server Error."""
    mock_agent_graph.side_effect = PlannerError("LLM returned malformed JSON")

    payload = {
        "task": {"prompt": "This will fail during planning"},
        "config": "default",
    }

    response = client.post("/api/launch", json=payload)

    assert response.status_code == 500
    assert "Agent Execution Failed" in response.json()["detail"]
    assert "LLM returned malformed JSON" in response.json()["detail"]
