# aegis/tests/tools/test_nmap_wrapper.py
"""
Tests for the nmap_port_scan wrapper tool.
"""
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError  # For testing failure propagation
from aegis.tools.primitives.primitive_system import RunLocalCommandInput
from aegis.tools.wrappers.wrapper_network import NmapScanInput, nmap_port_scan


@pytest.fixture
def mock_run_local_command_primitive(monkeypatch):
    """Mocks the underlying run_local_command primitive."""
    mock = MagicMock(return_value="Nmap scan output from primitive")
    # Patch where run_local_command is imported in the module under test
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_network.run_local_command", mock)
    return mock


def test_nmap_port_scan_builds_correct_command_success(
    mock_run_local_command_primitive,
):
    """Verify the tool constructs the nmap shell command correctly and calls the primitive."""
    input_data = NmapScanInput(
        targets=["127.0.0.1", "localhost"],
        ports="80,443",
        scan_type_flag="-sS",
        extra_flags="-T5 --max-retries 1",
    )

    result = nmap_port_scan(input_data)

    mock_run_local_command_primitive.assert_called_once()
    # Get the RunLocalCommandInput instance passed to the mocked primitive
    call_arg_input = mock_run_local_command_primitive.call_args[0][0]
    assert isinstance(call_arg_input, RunLocalCommandInput)

    # Assert on the command string within RunLocalCommandInput
    generated_command = call_arg_input.command
    assert generated_command.startswith("nmap -sS")
    assert "-p 80,443" in generated_command
    assert "-T5 --max-retries 1" in generated_command
    assert "127.0.0.1 localhost" in generated_command
    assert call_arg_input.shell is True  # nmap_port_scan sets shell=True

    assert result == "Nmap scan output from primitive"


def test_nmap_port_scan_primitive_fails(mock_run_local_command_primitive):
    """Verify that if the run_local_command primitive fails, the error propagates."""
    mock_run_local_command_primitive.side_effect = ToolExecutionError(
        "nmap primitive failed"
    )
    input_data = NmapScanInput(targets=["127.0.0.1"], ports="80", scan_type_flag="-sT")
    with pytest.raises(ToolExecutionError, match="nmap primitive failed"):
        nmap_port_scan(input_data)
    mock_run_local_command_primitive.assert_called_once()
