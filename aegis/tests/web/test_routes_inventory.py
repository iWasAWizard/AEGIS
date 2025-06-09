# aegis/tests/web/test_routes_inventory.py
"""
Unit tests for the tool inventory API route.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from aegis.registry import ToolEntry
from aegis.serve_dashboard import app

client = TestClient(app)


class GoodInput(BaseModel):
    arg1: str


class BadInput(BaseModel):
    # This lambda function is not JSON serializable, so schema() will fail
    default_factory: callable = lambda: "bad"


@pytest.fixture
def mock_tool_registry(monkeypatch):
    """Mocks the TOOL_REGISTRY with a set of test tools."""
    mock_registry = {
        "tool_a": ToolEntry(
            name="tool_a", run=MagicMock(), input_model=GoodInput,
            tags=["a"], description="Good tool A", category="cat1"
        ),
        "tool_b_bad_schema": ToolEntry(
            name="tool_b_bad_schema", run=MagicMock(), input_model=BadInput,
            tags=["b"], description="Tool with bad schema"
        ),
    }
    monkeypatch.setattr("aegis.web.routes_inventory.TOOL_REGISTRY", mock_registry)


def test_get_inventory(mock_tool_registry):
    """Verify the endpoint returns a correctly formatted list of tools."""
    response = client.get("/api/inventory")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2

    tool_a_data = next((t for t in data if t["name"] == "tool_a"), None)
    assert tool_a_data is not None
    assert tool_a_data["description"] == "Good tool A"
    assert tool_a_data["category"] == "cat1"
    assert "properties" in tool_a_data["input_schema"]  # Check schema was generated


def test_get_inventory_handles_bad_schema(mock_tool_registry):
    """Verify the endpoint gracefully handles a tool with an unserializable schema."""
    response = client.get("/api/inventory")
    assert response.status_code == 200
    data = response.json()

    bad_tool_data = next((t for t in data if t["name"] == "tool_b_bad_schema"), None)
    assert bad_tool_data is not None
    assert "error" in bad_tool_data["input_schema"]
    assert "Could not generate schema" in bad_tool_data["input_schema"]["error"]
