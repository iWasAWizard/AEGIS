# aegis/tests/tools/test_nmap_wrapper.py
"""
Tests for the nmap_port_scan wrapper tool.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.primitives.primitive_system import RunLocalCommandInput
from aegis.tools.wrappers.wrapper_network import NmapScanInput, nmap_port_scan


@pytest.fixture
def mock_run_local_command(monkeypatch):
    """Mocks the underlying run_local_command primitive."""
    mock = MagicMock(return_value="Nmap scan output")
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_network.run_local_command", mock)
    return mock


def test_nmap_port_scan_builds_correct_command(mock_run_local_command):
    """Verify the tool constructs the nmap shell command correctly."""
    input_data = NmapScanInput(
        targets=["127.0.0.1", "localhost"],
        ports="80,443",
        scan_type_flag="-sS",
        extra_flags="-T5 --max-retries 1",
    )

    nmap_port_scan(input_data)

    mock_run_local_command.assert_called_once()

    # Get the input that was passed to the mocked primitive
    call_args = mock_run_local_command.call_args[0][0]
    assert isinstance(call_args, RunLocalCommandInput)

    # Assert on the command string itself
    generated_command = call_args.command
    assert generated_command.startswith("nmap -sS")
    assert "-p 80,443" in generated_command
    assert "-T5 --max-retries 1" in generated_command
    assert "127.0.0.1 localhost" in generated_command
