# aegis/tests/web/test_routes_graphs.py
"""
Unit tests for the graph management API routes.
"""
import json
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegis.serve_dashboard import app

client = TestClient(app)


@pytest.fixture
def mock_graphs_dir(tmp_path: Path, monkeypatch):
    """Creates a temporary graphs directory with a sample file."""
    graphs_dir = tmp_path / "graphs"
    graphs_dir.mkdir()

    graph_content = {"entrypoint": "start", "nodes": []}
    (graphs_dir / "test_graph.json").write_text(json.dumps(graph_content))

    monkeypatch.setattr("aegis.web.routes_graphs.GRAPH_DIR", str(graphs_dir))
    return graphs_dir


def test_list_graphs(mock_graphs_dir):
    """Verify the endpoint lists existing graph files."""
    response = client.get("/api/graphs/")
    assert response.status_code == 200
    data = response.json()
    assert "test_graph.json" in data


def test_view_graph(mock_graphs_dir):
    """Verify the endpoint can retrieve and parse a specific graph file."""
    response = client.get("/api/graphs/view?name=test_graph.json")
    assert response.status_code == 200
    data = response.json()
    assert data["entrypoint"] == "start"


def test_view_graph_not_found():
    """Test that a 404 is returned for a non-existent graph."""
    response = client.get("/api/graphs/view?name=not_real.json")
    assert response.status_code == 404


def test_upload_graph(mock_graphs_dir):
    """Verify that a file can be successfully uploaded."""
    upload_content = b'{"entrypoint": "new", "nodes": [{"id": "new"}]}'
    file_to_upload = ("new_graph.json", BytesIO(upload_content), "application/json")

    with TestClient(app) as client:
        response = client.post("/api/graphs/upload", files={"file": file_to_upload})

    assert response.status_code == 200
    assert response.json()["filename"] == "new_graph.json"

    # Check that the file was actually created in our temp dir
    new_file_path = mock_graphs_dir / "new_graph.json"
    assert new_file_path.is_file()
    assert new_file_path.read_bytes() == upload_content
