# aegis/tests/tools/primitives/test_primitive_network.py
"""
Unit tests for the network primitive tools.
"""
import socket
import subprocess
from unittest.mock import MagicMock

import pytest
import requests

from aegis.exceptions import ToolExecutionError
from aegis.tools.primitives.primitive_network import (
    send_wake_on_lan, WakeOnLANInput,
    http_request, HttpRequestInput,
    check_port_status, CheckPortStatusInput
)


# --- Fixtures ---

@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Fixture to mock subprocess.run."""
    mock = MagicMock()
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


@pytest.fixture
def mock_requests(monkeypatch):
    """Fixture to mock requests.request."""
    mock = MagicMock()
    monkeypatch.setattr(requests, "request", mock)
    return mock


@pytest.fixture
def mock_socket(monkeypatch):
    """Fixture to mock socket.socket."""
    mock_socket_instance = MagicMock()
    mock_socket_class = MagicMock(return_value=mock_socket_instance)
    # This makes 'with socket.socket(...) as s:' work
    mock_socket_instance.__enter__.return_value = mock_socket_instance
    monkeypatch.setattr(socket, "socket", mock_socket_class)
    return mock_socket_instance


# --- Tests ---

def test_send_wake_on_lan(mock_subprocess_run):
    """Verify send_wake_on_lan constructs the correct shell command."""
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="wol output", stderr="")
    input_data = WakeOnLANInput(mac_address="00:11:22:33:44:55")
    send_wake_on_lan(input_data)

    mock_subprocess_run.assert_called_once_with(
        ["wakeonlan", "00:11:22:33:44:55"], capture_output=True, text=True, timeout=10, check=False
    )


def test_http_request_success(mock_requests):
    """Verify http_request correctly calls requests.request."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"status": "ok"}'
    mock_requests.return_value = mock_response

    input_data = HttpRequestInput(method="POST", url="http://test.com/api", body="payload")
    result = http_request(input_data)

    mock_requests.assert_called_once_with(
        method="POST",
        url="http://test.com/api",
        headers=None,
        params=None,
        data=b"payload",  # Should be bytes
        timeout=30
    )
    assert 'Status: 200' in result
    assert '{"status": "ok"}' in result


def test_http_request_failure(mock_requests):
    """Verify http_request wraps a RequestException in ToolExecutionError."""
    mock_requests.side_effect = requests.exceptions.RequestException("Connection failed")

    input_data = HttpRequestInput(method="GET", url="http://unreachable.com")
    with pytest.raises(ToolExecutionError, match="HTTP request failed: Connection failed"):
        http_request(input_data)


def test_check_port_status_open(mock_socket):
    """Verify check_port_status returns 'Open' on a successful connection."""
    mock_socket.connect_ex.return_value = 0  # 0 means success
    input_data = CheckPortStatusInput(host="localhost", port=80)
    result = check_port_status(input_data)

    mock_socket.connect_ex.assert_called_once_with(("localhost", 80))
    assert "is Open" in result


def test_check_port_status_closed(mock_socket):
    """Verify check_port_status returns 'Closed' on a failed connection."""
    mock_socket.connect_ex.return_value = 1  # Non-zero means failure
    input_data = CheckPortStatusInput(host="localhost", port=8080)
    result = check_port_status(input_data)

    mock_socket.connect_ex.assert_called_once_with(("localhost", 8080))
    assert "is Closed" in result


def test_check_port_status_gaierror(mock_socket):
    """Verify check_port_status handles a hostname resolution error."""
    mock_socket.connect_ex.side_effect = socket.gaierror("Name or service not known")
    input_data = CheckPortStatusInput(host="invalid-hostname", port=80)
    result = check_port_status(input_data)

    assert "[ERROR] Hostname 'invalid-hostname' could not be resolved" in result
