# aegis/tests/web/test_routes_resume.py
"""
Unit tests for the task resume API route.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from aegis.serve_dashboard import app
from aegis.web.routes_launch import INTERRUPTED_STATES

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_interrupted_states():
    """Fixture to ensure the INTERRUPTED_STATES dict is empty before each test."""
    INTERRUPTED_STATES.clear()
    yield
    INTERRUPTED_STATES.clear()


def test_resume_task_success():
    """Test a successful resumption of a paused task."""
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {
        "task_id": "task-to-resume",
        "final_summary": "Resumed and completed.",
        "history": [],
    }

    INTERRUPTED_STATES["task-to-resume"] = {"graph": mock_graph, "state": {}}

    payload = {"task_id": "task-to-resume", "human_feedback": "Proceed as planned."}
    response = client.post("/api/resume", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Resumed and completed."
    mock_graph.ainvoke.assert_awaited_once()
    # Check that the feedback was injected
    assert mock_graph.ainvoke.call_args.args[0]["human_feedback"] == "Proceed as planned."


def test_resume_task_not_found():
    """Test that a 404 is returned if the task ID is not in the interrupted store."""
    payload = {"task_id": "non-existent-task", "human_feedback": "Go"}
    response = client.post("/api/resume", json=payload)
    assert response.status_code == 404
    assert "Paused task not found" in response.json()["detail"]