# aegis/tests/tools/wrappers/test_fuzz_tools.py
"""
Unit tests for the fuzzing wrapper tools.
"""
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import requests
from pydantic import BaseModel

from aegis.registry import ToolEntry, TOOL_REGISTRY
from aegis.tools.wrappers.fuzz import (
    generate_payload,
    fuzz_external_command,
    FuzzExternalCommandInput,
    fuzz_file_input,
    FuzzFileInputInput,
    fuzz_api_request,
    FuzzAPIRequestInput,
    fuzz_tool_via_registry,
    FuzzToolRegistryInput,
)


# --- Tests for Helper ---


@pytest.mark.parametrize(
    "mode, validator",
    [
        ("ascii", lambda p: p.isalnum()),
        ("json", lambda p: isinstance(json.loads(p), dict)),
        ("emoji", lambda p: True),  # Hard to validate charset easily
        ("bytes", lambda p: True),
    ],
)
def test_generate_payload(mode, validator):
    """Verify the payload generator creates valid payloads for each mode."""
    payload = generate_payload(mode, 50)
    assert isinstance(payload, str)
    assert len(payload) > 0
    assert validator(payload)


# --- Tests for Tools ---


def test_fuzz_external_command(monkeypatch):
    """Verify fuzz_external_command loops correctly and summarizes failures."""
    mock_run = MagicMock(
        side_effect=[
            subprocess.CompletedProcess(args=[], returncode=0),  # Success
            subprocess.CompletedProcess(args=[], returncode=1),  # Failure
            subprocess.CompletedProcess(args=[], returncode=0),  # Success
        ]
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    input_data = FuzzExternalCommandInput(command="test_cmd {}", iterations=3)
    result = fuzz_external_command(input_data)

    assert mock_run.call_count == 3
    assert result["summary"]["attempted"] == 3
    assert result["summary"]["failures"] == 1


@patch("tempfile.NamedTemporaryFile")
def test_fuzz_file_input(mock_temp_file, monkeypatch):
    """Verify fuzz_file_input creates and uses a temporary file."""
    mock_run = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0)
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    # Mock the file context manager
    mock_file_handle = MagicMock()
    mock_temp_file.return_value.__enter__.return_value = mock_file_handle
    mock_file_handle.name = "/tmp/fakefile.fuzz"

    input_data = FuzzFileInputInput(command_template="cat {}", iterations=1)
    fuzz_file_input(input_data)

    mock_file_handle.write.assert_called_once()
    mock_run.assert_called_once()
    assert "cat /tmp/fakefile.fuzz" in mock_run.call_args[0]


def test_fuzz_api_request(monkeypatch):
    """Verify fuzz_api_request correctly interprets HTTP status codes as failures."""
    mock_response_ok = MagicMock(status_code=200, text="OK")
    mock_response_fail = MagicMock(status_code=500, text="Error")

    mock_request = MagicMock(side_effect=[mock_response_ok, mock_response_fail])
    monkeypatch.setattr(requests, "request", mock_request)

    input_data = FuzzAPIRequestInput(url="http://test.com/api", iterations=2)
    result = fuzz_api_request(input_data)

    assert mock_request.call_count == 2
    assert result["summary"]["requests_sent"] == 2
    assert result["summary"]["failures"] == 1


def test_fuzz_tool_via_registry(monkeypatch):
    """Verify fuzz_tool_via_registry correctly calls a registered tool and handles errors."""

    class MockToolInput(BaseModel):
        pass

    # Mock a tool that succeeds once, then fails
    mock_run_func = MagicMock(side_effect=["success", Exception("tool failed")])

    mock_entry = ToolEntry(
        name="test_tool",
        run=mock_run_func,
        input_model=MockToolInput,
        tags=[],
        description="",
    )
    monkeypatch.setitem(TOOL_REGISTRY, "test_tool", mock_entry)

    input_data = FuzzToolRegistryInput(tool_name="test_tool", iterations=2)
    result = fuzz_tool_via_registry(input_data)

    assert mock_run_func.call_count == 2
    assert result["summary"]["invocations"] == 2
    assert result["summary"]["failures"] == 1
    assert "error" in result["results"][1]
