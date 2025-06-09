# aegis/tests/web/test_routes_reports.py
"""
Unit tests for the report viewing API routes.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegis.serve_dashboard import app

client = TestClient(app)


@pytest.fixture
def mock_report_dir(tmp_path: Path, monkeypatch):
    """Creates a temporary reports directory with sample files."""
    report_dir = tmp_path / "reports"
    report_dir.mkdir()

    # A valid report file
    (report_dir / "report-001.md").write_text("# Test Report")
    # A non-report file that should be ignored
    (report_dir / "data.csv").write_text("a,b,c")
    # An empty directory that should be ignored
    (report_dir / "empty_dir").mkdir()

    monkeypatch.setattr("aegis.web.routes_reports.REPORT_DIR", str(report_dir))
    return report_dir


def test_list_reports(mock_report_dir):
    """Verify that only valid report files are listed."""
    response = client.get("/api/reports/")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0] == "report-001.md"


def test_view_report_success(mock_report_dir):
    """Verify that a valid report can be successfully viewed."""
    response = client.get("/api/reports/view?name=report-001.md")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "# Test Report"


def test_view_report_not_found():
    """Verify that requesting a non-existent report returns a 404."""
    # This test doesn't need the mock dir, as it's testing the failure case
    response = client.get("/api/reports/view?name=non-existent.md")
    assert response.status_code == 404
    assert "Report not found" in response.json()["detail"]
