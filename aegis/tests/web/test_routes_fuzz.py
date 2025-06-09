# aegis/tests/web/test_routes_fuzz.py
"""
Unit tests for the fuzzing API routes.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from aegis.registry import TOOL_REGISTRY, ToolEntry
from aegis.serve_dashboard import app

client = TestClient(app)


class MockFuzzInput(BaseModel):
    iterations: int


class MockOtherInput(BaseModel):
    pass


@pytest.fixture(autouse=True)
def mock_fuzz_tool_in_registry(monkeypatch):
    """Mocks the TOOL_REGISTRY to contain specific tools for testing."""
    fuzz_tool_run_mock = MagicMock(return_value={"summary": "fuzz complete"})

    mock_registry = {
        "test_fuzz_tool": ToolEntry(
            name="test_fuzz_tool",
            run=fuzz_tool_run_mock,
            input_model=MockFuzzInput,
            tags=["fuzz", "test"],
            description="A test fuzz tool."
        ),
        "not_a_fuzz_tool": ToolEntry(
            name="not_a_fuzz_tool",
            run=MagicMock(),
            input_model=MockOtherInput,
            tags=["other"],
            description="A regular tool."
        )
    }

    # Temporarily replace the real registry with our mock
    monkeypatch.setattr("aegis.web.routes_fuzz.TOOL_REGISTRY", mock_registry)
    yield fuzz_tool_run_mock


def test_list_fuzz_tools():
    """Verify the endpoint returns only tools tagged with 'fuzz'."""
    response = client.get("/api/fuzz/")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0] == "test_fuzz_tool"


def test_run_fuzz_tool_success(mock_fuzz_tool_in_registry):
    """Verify a successful request to run a valid fuzz tool."""
    payload = {
        "tool_name": "test_fuzz_tool",
        "payload": {"iterations": 10}
    }
    response = client.post("/api/fuzz/run", json=payload)

    assert response.status_code == 200
    assert response.json() == {"result": {"summary": "fuzz complete"}}
    mock_fuzz_tool_in_registry.assert_called_once()


def test_run_fuzz_tool_not_found():
    """Test 404 error when the requested tool does not exist."""
    payload = {
        "tool_name": "non_existent_tool",
        "payload": {}
    }
    response = client.post("/api/fuzz/run", json=payload)
    assert response.status_code == 404


def test_run_fuzz_tool_not_a_fuzz_tool():
    """Test 403 error when trying to run a tool not tagged with 'fuzz'."""
    payload = {
        "tool_name": "not_a_fuzz_tool",
        "payload": {}
    }
    response = client.post("/api/fuzz/run", json=payload)
    assert response.status_code == 403


def test_run_fuzz_tool_validation_error(monkeypatch):
    """Test 400 error when the payload fails Pydantic validation."""
    # Mock the input model to raise a validation error
    mock_input_model = MagicMock()
    mock_input_model.side_effect = ValidationError.from_exception_data(
        title="MockValidationError", line_errors=[]
    )

    # Get the existing tool and monkeypatch its input model for this test
    fuzz_tool_entry = TOOL_REGISTRY["test_fuzz_tool"]
    monkeypatch.setattr(fuzz_tool_entry, "input_model", mock_input_model)

    payload = {
        "tool_name": "test_fuzz_tool",
        "payload": {"wrong_arg": 10}  # This payload will cause the validation error
    }
    response = client.post("/api/fuzz/run", json=payload)
    assert response.status_code == 400
    assert "Invalid payload" in response.json()["detail"]
