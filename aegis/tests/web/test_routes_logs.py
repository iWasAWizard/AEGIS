# aegis/tests/web/test_routes_logs.py
"""
Unit tests for the miscellaneous status and debug API routes.
"""
from fastapi.testclient import TestClient

from aegis.serve_dashboard import app

client = TestClient(app)


def test_system_status():
    """Verify the /status endpoint returns a valid status object."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()

    assert "server_time" in data
    assert "platform" in data
    assert "node" in data
    assert "python_version" in data
    assert "cwd" in data
    assert "safe_mode" in data


def test_echo_post():
    """Verify the /echo endpoint returns the exact payload it receives."""
    payload = {"key": "value", "nested": {"a": 1}}
    response = client.post("/api/echo", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "echo" in data
    assert data["echo"] == payload
