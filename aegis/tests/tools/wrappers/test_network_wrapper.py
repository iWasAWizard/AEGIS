# aegis/tests/tools/wrappers/test_network_wrapper.py
"""
Unit tests for the high-level network wrapper tools.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from aegis.exceptions import ToolExecutionError  # For testing failure propagation
from aegis.tools.primitives.primitive_network import HttpRequestInput
from aegis.tools.primitives.primitive_system import RunLocalCommandInput
from aegis.tools.wrappers.wrapper_network import (
    http_post_json,
    HttpPostJsonInput,
    upload_to_grafana,
    GrafanaUploadInput,
    nmap_port_scan,
    NmapScanInput,
)


@pytest.fixture
def mock_http_request_primitive(monkeypatch):
    """Mocks the underlying http_request primitive."""
    mock = MagicMock(return_value="HTTP OK from primitive")
    # Patch where http_request is imported in the module under test
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_network.http_request", mock)
    return mock


@pytest.fixture
def mock_run_local_command_primitive(monkeypatch):
    """Mocks the underlying run_local_command primitive."""
    mock = MagicMock(return_value="Nmap scan output from primitive")
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_network.run_local_command", mock)
    return mock


# --- Tests ---


def test_http_post_json_success(mock_http_request_primitive):
    """Verify the wrapper correctly calls http_request primitive with JSON payload."""
    payload_dict = {"key": "value", "id": 123}
    input_data = HttpPostJsonInput(
        url="http://api.test/submit", payload=payload_dict, timeout=20
    )

    result = http_post_json(input_data)

    mock_http_request_primitive.assert_called_once()
    call_arg_input = mock_http_request_primitive.call_args[0][0]

    assert isinstance(call_arg_input, HttpRequestInput)
    assert call_arg_input.method == "POST"
    assert call_arg_input.url == "http://api.test/submit"
    assert call_arg_input.headers.get("Content-Type") == "application/json"  # type: ignore
    assert call_arg_input.body is None  # Should use json_payload
    assert call_arg_input.json_payload == payload_dict
    assert call_arg_input.timeout == 20

    assert result == "HTTP OK from primitive"


def test_http_post_json_primitive_fails(mock_http_request_primitive):
    """Verify error from http_request primitive propagates."""
    mock_http_request_primitive.side_effect = ToolExecutionError(
        "http_request primitive failed"
    )
    input_data = HttpPostJsonInput(url="http://api.test/submit", payload={"a": 1})
    with pytest.raises(ToolExecutionError, match="http_request primitive failed"):
        http_post_json(input_data)
    mock_http_request_primitive.assert_called_once()


def test_upload_to_grafana_success(mock_http_request_primitive):
    """Verify the wrapper calls http_request primitive with correct headers for Grafana."""
    payload_dict = {"message": "deployment complete"}
    input_data = GrafanaUploadInput(
        url="http://grafana/api/annotations",
        payload=payload_dict,
        token="my-secret-token",
        timeout=25,
    )

    result = upload_to_grafana(input_data)

    mock_http_request_primitive.assert_called_once()
    call_arg_input = mock_http_request_primitive.call_args[0][0]

    assert isinstance(call_arg_input, HttpRequestInput)
    assert call_arg_input.method == "POST"
    assert call_arg_input.url == "http://grafana/api/annotations"
    assert call_arg_input.headers.get("Content-Type") == "application/json"  # type: ignore
    assert call_arg_input.headers.get("Authorization") == "Bearer my-secret-token"  # type: ignore
    assert call_arg_input.json_payload == payload_dict
    assert call_arg_input.timeout == 25

    assert result == "HTTP OK from primitive"


def test_upload_to_grafana_primitive_fails(mock_http_request_primitive):
    """Verify error from http_request primitive propagates for Grafana tool."""
    mock_http_request_primitive.side_effect = ToolExecutionError(
        "http_request primitive failed for grafana"
    )
    input_data = GrafanaUploadInput(url="http://grafana/api", payload={}, token="token")
    with pytest.raises(
        ToolExecutionError, match="http_request primitive failed for grafana"
    ):
        upload_to_grafana(input_data)
    mock_http_request_primitive.assert_called_once()


def test_nmap_port_scan_success(mock_run_local_command_primitive):
    """Verify the wrapper constructs the correct nmap shell command and calls primitive."""
    input_data = NmapScanInput(
        targets=["127.0.0.1", "localhost"],
        ports="80,443,8000",
        scan_type_flag="-sS",
        extra_flags="-T5",
    )

    result = nmap_port_scan(input_data)

    mock_run_local_command_primitive.assert_called_once()
    call_arg_input = mock_run_local_command_primitive.call_args[0][0]

    assert isinstance(call_arg_input, RunLocalCommandInput)
    command = call_arg_input.command

    assert command.startswith("nmap -sS")
    assert "-p 80,443,8000" in command
    assert "-T5" in command
    assert "127.0.0.1 localhost" in command
    assert call_arg_input.shell is True

    assert result == "Nmap scan output from primitive"


def test_nmap_port_scan_primitive_fails(mock_run_local_command_primitive):
    """Verify error from run_local_command primitive propagates for nmap tool."""
    mock_run_local_command_primitive.side_effect = ToolExecutionError(
        "run_local_command primitive failed for nmap"
    )
    input_data = NmapScanInput(targets=["host"], ports="80", scan_type_flag="-sT")
    with pytest.raises(
        ToolExecutionError, match="run_local_command primitive failed for nmap"
    ):
        nmap_port_scan(input_data)
    mock_run_local_command_primitive.assert_called_once()
