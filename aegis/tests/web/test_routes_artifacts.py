# aegis/tests/web/test_routes_artifacts.py
"""
Unit tests for the task artifact API routes.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegis.serve_dashboard import app

client = TestClient(app)


@pytest.fixture
def mock_reports_dir(tmp_path: Path, monkeypatch):
    """Creates a temporary reports and logs directory structure for testing."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    # Task 1: Has all artifacts
    task1_dir = reports_dir / "task-001"
    task1_dir.mkdir()
    (task1_dir / "summary.md").write_text("# Summary 1")
    (task1_dir / "provenance.json").write_text(json.dumps({"task_id": "task-001"}))

    # Task 2: Only has a provenance file
    task2_dir = reports_dir / "task-002"
    task2_dir.mkdir()
    (task2_dir / "provenance.json").write_text(
        json.dumps({"task_id": "task-002", "final_status": "FAILURE"})
    )

    # Task 3: Has a malformed provenance file
    task3_dir = reports_dir / "task-003"
    task3_dir.mkdir()
    (task3_dir / "provenance.json").write_text("{'not_json': True}")  # Invalid JSON

    # Monkeypatch the constants in the routes module
    monkeypatch.setattr("aegis.web.routes_artifacts.REPORTS_DIR", reports_dir)


def test_list_artifacts(mock_reports_dir):
    """Test that the list_artifacts endpoint correctly identifies existing artifacts."""
    response = client.get("/api/artifacts")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3

    task1_data = next((item for item in data if item["task_id"] == "task-001"), None)
    task2_data = next((item for item in data if item["task_id"] == "task-002"), None)

    assert task1_data is not None
    assert task1_data["has_summary"] is True
    assert task1_data["has_provenance"] is True

    assert task2_data is not None
    assert task2_data["has_summary"] is False
    assert task2_data["has_provenance"] is True


def test_get_summary_artifact(mock_reports_dir):
    """Test retrieving a valid summary artifact."""
    response = client.get("/api/artifacts/task-001/summary")
    assert response.status_code == 200
    assert response.text == "# Summary 1"


def test_get_summary_artifact_not_found(mock_reports_dir):
    """Test that a 404 is returned for a missing summary."""
    response = client.get("/api/artifacts/task-002/summary")
    assert response.status_code == 404


def test_get_provenance_artifact(mock_reports_dir):
    """Test retrieving a valid provenance artifact."""
    response = client.get("/api/artifacts/task-001/provenance")
    assert response.status_code == 200
    assert response.json() == {"task_id": "task-001"}


def test_get_provenance_malformed(mock_reports_dir):
    """Test that a 500 is returned for a malformed provenance file."""
    response = client.get("/api/artifacts/task-003/provenance")
    assert response.status_code == 500
    assert "Error reading or parsing" in response.json()["detail"]
