# aegis/tests/tools/wrappers/test_network_wrapper.py
"""
Unit tests for the high-level network wrapper tools.
"""
import json
from unittest.mock import MagicMock

import pytest

from aegis.tools.primitives.primitive_network import HttpRequestInput
from aegis.tools.primitives.primitive_system import RunLocalCommandInput
from aegis.tools.wrappers.wrapper_network import (
    http_post_json, HttpPostJsonInput,
    upload_to_grafana, GrafanaUploadInput,
    nmap_port_scan, NmapScanInput,
)


# --- Fixtures ---

@pytest.fixture
def mock_http_request(monkeypatch):
    """Mocks the underlying http_request primitive."""
    mock = MagicMock(return_value="HTTP OK")
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_network.http_request", mock)
    return mock


@pytest.fixture
def mock_run_local_command(monkeypatch):
    """Mocks the underlying run_local_command primitive."""
    mock = MagicMock(return_value="Nmap scan output")
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_network.run_local_command", mock)
    return mock


# --- Tests ---

def test_http_post_json(mock_http_request):
    """Verify the wrapper correctly serializes JSON and adds the correct header."""
    payload_dict = {"key": "value", "id": 123}
    input_data = HttpPostJsonInput(url="http://api.test/submit", payload=payload_dict)

    http_post_json(input_data)

    mock_http_request.assert_called_once()
    call_args = mock_http_request.call_args[0][0]

    assert isinstance(call_args, HttpRequestInput)
    assert call_args.method == "POST"
    assert call_args.url == "http://api.test/submit"
    assert call_args.headers["Content-Type"] == "application/json"
    # Verify the body was serialized from dict to string
    assert call_args.body == json.dumps(payload_dict)


def test_upload_to_grafana(mock_http_request):
    """Verify the wrapper adds the correct Content-Type and Authorization headers."""
    payload_dict = {"message": "deployment complete"}
    input_data = GrafanaUploadInput(
        url="http://grafana/api/annotations",
        payload=payload_dict,
        token="my-secret-token"
    )

    upload_to_grafana(input_data)

    mock_http_request.assert_called_once()
    call_args = mock_http_request.call_args[0][0]

    assert isinstance(call_args, HttpRequestInput)
    assert call_args.headers["Content-Type"] == "application/json"
    assert call_args.headers["Authorization"] == "Bearer my-secret-token"


def test_nmap_port_scan(mock_run_local_command):
    """Verify the wrapper constructs the correct nmap shell command."""
    input_data = NmapScanInput(
        targets=["127.0.0.1", "localhost"],
        ports="80,443,8000",
        scan_type_flag="-sS",
        extra_flags="-T5"
    )

    nmap_port_scan(input_data)

    mock_run_local_command.assert_called_once()
    call_args = mock_run_local_command.call_args[0][0]

    assert isinstance(call_args, RunLocalCommandInput)
    command = call_args.command

    assert command.startswith("nmap -sS")
    assert "-p 80,443,8000" in command
    assert "-T5" in command
    assert "127.0.0.1 localhost" in command
