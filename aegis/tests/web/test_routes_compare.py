# aegis/tests/web/test_routes_compare.py
"""
Unit tests for the report comparison API route.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegis.serve_dashboard import app

client = TestClient(app)


@pytest.fixture
def mock_compare_reports(tmp_path: Path, monkeypatch):
    """Creates a temporary reports directory with two summaries to compare."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    # Task 1 Summary
    task1_dir = reports_dir / "task-comp-001"
    task1_dir.mkdir()
    (task1_dir / "summary.md").write_text("line 1\nline 2 common\nline 3 old")

    # Task 2 Summary
    task2_dir = reports_dir / "task-comp-002"
    task2_dir.mkdir()
    (task2_dir / "summary.md").write_text("line 1\nline 2 common\nline 3 new")

    # Monkeypatch the REPORTS_DIR constant in the routes module
    monkeypatch.setattr("aegis.web.routes_compare.REPORTS_DIR", reports_dir)


def test_compare_reports_success(mock_compare_reports):
    """Test successful comparison of two existing reports."""
    payload = ["task-comp-001", "task-comp-002"]
    response = client.post("/api/compare_reports", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["task1_id"] == "task-comp-001"
    assert data["task2_id"] == "task-comp-002"

    diff_str = "\n".join(data["diff"])
    assert "--- task-comp-001/summary.md" in diff_str
    assert "+++ task-comp-002/summary.md" in diff_str
    assert "-line 3 old" in diff_str
    assert "+line 3 new" in diff_str
    assert " line 2 common" in diff_str


@pytest.mark.parametrize("payload", [
    ["task-comp-001"],  # Too few IDs
    ["t1", "t2", "t3"],  # Too many IDs
    [],  # Empty list
])
def test_compare_reports_invalid_input(mock_compare_reports, payload):
    """Test that the endpoint rejects requests with incorrect numbers of task IDs."""
    response = client.post("/api/compare_reports", json=payload)
    assert response.status_code == 400
    assert "provide exactly two task IDs" in response.json()["detail"]


def test_compare_reports_file_not_found(mock_compare_reports):
    """Test that a 404 is returned if one of the summary files does not exist."""
    payload = ["task-comp-001", "non-existent-task"]
    response = client.post("/api/compare_reports", json=payload)

    assert response.status_code == 404
    assert "Summary for task 'non-existent-task' not found" in response.json()["detail"]
