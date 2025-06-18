# aegis/tests/tools/primitives/test_network_primitive.py
"""
Unit tests for the network primitive tools.
"""
import socket
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import requests

from aegis.exceptions import ToolExecutionError
from aegis.tools.primitives.primitive_network import (
    send_wake_on_lan,
    WakeOnLANInput,
    http_request,
    HttpRequestInput,
    check_port_status,
    CheckPortStatusInput,
)


@pytest.fixture
def mock_subprocess_run_for_wol(monkeypatch):
    """Fixture to mock subprocess.run specifically for send_wake_on_lan."""
    mock = MagicMock()
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


@pytest.fixture
def mock_http_executor_request(monkeypatch):
    """Fixture to mock HttpExecutor's request method."""
    mock_response_obj = MagicMock(spec=requests.Response)
    mock_response_obj.status_code = 200
    mock_response_obj.text = '{"status": "ok"}'

    mock_request_method = MagicMock(return_value=mock_response_obj)
    monkeypatch.setattr(
        "aegis.executors.http.HttpExecutor.request", mock_request_method
    )
    return mock_request_method


@pytest.fixture
def mock_socket(monkeypatch):
    """Fixture to mock socket.socket for check_port_status."""
    mock_socket_instance = MagicMock()
    mock_socket_class = MagicMock(return_value=mock_socket_instance)
    mock_socket_instance.__enter__.return_value = mock_socket_instance
    monkeypatch.setattr(socket, "socket", mock_socket_class)
    return mock_socket_instance


# --- Tests ---


def test_send_wake_on_lan_success(mock_subprocess_run_for_wol):
    """Verify send_wake_on_lan constructs the correct shell command and returns output."""
    mock_subprocess_run_for_wol.return_value = MagicMock(
        returncode=0, stdout="wol output", stderr=""
    )
    input_data = WakeOnLANInput(mac_address="00:11:22:33:44:55")
    result = send_wake_on_lan(input_data)

    mock_subprocess_run_for_wol.assert_called_once_with(
        ["wakeonlan", "00:11:22:33:44:55"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result == "wol output"


def test_send_wake_on_lan_success_no_output(mock_subprocess_run_for_wol):
    """Verify send_wake_on_lan returns custom message if command output is empty."""
    mock_subprocess_run_for_wol.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )
    input_data = WakeOnLANInput(mac_address="00:11:22:33:44:55")
    result = send_wake_on_lan(input_data)
    assert result == "Wake-on-LAN packet sent to 00:11:22:33:44:55."


def test_send_wake_on_lan_failure_rc(mock_subprocess_run_for_wol):
    """Verify send_wake_on_lan raises ToolExecutionError on non-zero return code."""
    mock_subprocess_run_for_wol.return_value = MagicMock(
        returncode=1, stdout="", stderr="wakeonlan error"
    )
    input_data = WakeOnLANInput(mac_address="00:11:22:33:44:55")
    with pytest.raises(
        ToolExecutionError,
        match="'wakeonlan' command failed with RC 1. Output: \n\\[STDERR\\]\nwakeonlan error",
    ):
        send_wake_on_lan(input_data)


def test_send_wake_on_lan_timeout(mock_subprocess_run_for_wol):
    """Verify send_wake_on_lan raises ToolExecutionError on timeout."""
    mock_subprocess_run_for_wol.side_effect = subprocess.TimeoutExpired("wakeonlan", 10)
    input_data = WakeOnLANInput(mac_address="00:11:22:33:44:55")
    with pytest.raises(
        ToolExecutionError,
        match="'wakeonlan' command timed out for MAC 00:11:22:33:44:55.",
    ):
        send_wake_on_lan(input_data)


def test_send_wake_on_lan_not_found(mock_subprocess_run_for_wol):
    """Verify send_wake_on_lan raises ToolExecutionError if 'wakeonlan' command is not found."""
    mock_subprocess_run_for_wol.side_effect = FileNotFoundError
    input_data = WakeOnLANInput(mac_address="00:11:22:33:44:55")
    with pytest.raises(
        ToolExecutionError,
        match="'wakeonlan' command was not found. Please ensure it is installed and in PATH.",
    ):
        send_wake_on_lan(input_data)


def test_http_request_success_json_payload(mock_http_executor_request):
    """Verify http_request calls HttpExecutor.request correctly for JSON payload."""
    input_data = HttpRequestInput(
        method="POST",
        url="http://test.com/api",
        json_payload={"key": "value"},
        timeout=15,
    )
    result_str = http_request(input_data)

    mock_http_executor_request.assert_called_once_with(
        method="POST",
        url="http://test.com/api",
        headers={},
        params={},
        data=None,
        json_payload={"key": "value"},
        timeout=15,
    )
    assert "Status: 200" in result_str
    assert '{"status": "ok"}' in result_str


def test_http_request_success_raw_body(mock_http_executor_request):
    """Verify http_request calls HttpExecutor.request correctly for raw body."""
    input_data = HttpRequestInput(
        method="PUT", url="http://test.com/data", body="raw_payload", timeout=10
    )
    result_str = http_request(input_data)

    mock_http_executor_request.assert_called_once_with(
        method="PUT",
        url="http://test.com/data",
        headers={},
        params={},
        data=b"raw_payload",
        json_payload=None,
        timeout=10,
    )
    assert "Status: 200" in result_str
    assert '{"status": "ok"}' in result_str


def test_http_request_failure_propagates(mock_http_executor_request):
    """Verify ToolExecutionError from HttpExecutor.request propagates."""
    mock_http_executor_request.side_effect = ToolExecutionError(
        "Executor HTTP request failed"
    )
    input_data = HttpRequestInput(method="GET", url="http://unreachable.com")

    with pytest.raises(ToolExecutionError, match="Executor HTTP request failed"):
        http_request(input_data)


def test_check_port_status_open(mock_socket):
    """Verify check_port_status returns 'Open' on a successful connection."""
    mock_socket.connect_ex.return_value = 0
    input_data = CheckPortStatusInput(host="localhost", port=80, timeout=1.0)
    result = check_port_status(input_data)

    mock_socket.settimeout.assert_called_once_with(1.0)
    mock_socket.connect_ex.assert_called_once_with(("localhost", 80))
    assert result == "Port 80 on localhost is Open."


def test_check_port_status_closed(mock_socket):
    """Verify check_port_status returns 'Closed or Filtered' on a failed connection."""
    mock_socket.connect_ex.return_value = 1
    input_data = CheckPortStatusInput(host="localhost", port=8080)
    result = check_port_status(input_data)

    mock_socket.connect_ex.assert_called_once_with(("localhost", 8080))
    assert result == "Port 8080 on localhost is Closed or Filtered."


def test_check_port_status_timeout(mock_socket):
    """Verify check_port_status returns 'Filtered (Connection Timed Out)' on socket timeout."""
    mock_socket.connect_ex.side_effect = socket.timeout
    input_data = CheckPortStatusInput(host="remotehost", port=443, timeout=0.5)
    result = check_port_status(input_data)
    assert result == "Port 443 on remotehost is Filtered (Connection Timed Out)."


def test_check_port_status_gaierror(mock_socket):
    """Verify check_port_status raises ToolExecutionError on hostname resolution error."""
    mock_socket.connect_ex.side_effect = socket.gaierror("Name or service not known")
    input_data = CheckPortStatusInput(host="invalid-hostname", port=80)
    with pytest.raises(
        ToolExecutionError,
        match="Hostname 'invalid-hostname' could not be resolved: Name or service not known",
    ):
        check_port_status(input_data)


def test_check_port_status_socket_error(mock_socket):
    """Verify check_port_status raises ToolExecutionError on other socket errors."""
    mock_socket.connect_ex.side_effect = socket.error("Connection refused")
    input_data = CheckPortStatusInput(host="localhost", port=12345)
    with pytest.raises(
        ToolExecutionError,
        match="A socket error occurred while checking localhost:12345: Connection refused",
    ):
        check_port_status(input_data)
