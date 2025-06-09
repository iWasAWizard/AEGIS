# aegis/tests/tools/primitives/test_system_primitive.py
"""
Unit tests for the local system primitive tools.
"""
import subprocess
from unittest.mock import MagicMock, mock_open

import psutil
import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.primitives.primitive_system import (
    kill_local_process, KillProcessInput,
    run_local_command, RunLocalCommandInput,
    get_local_memory_info, GetLocalMemoryInfoInput,
    get_random_bytes_as_hex, GetRandomBytesInput
)


# --- Fixtures ---

@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Fixture to mock subprocess.run."""
    mock = MagicMock()
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


@pytest.fixture
def mock_psutil_memory(monkeypatch):
    """Fixture to mock psutil.virtual_memory."""
    mock_mem = MagicMock()
    mock_mem.total = 8 * 1024 ** 3  # 8 GB
    mock_mem.available = 4 * 1024 ** 3  # 4 GB
    mock_mem.used = 4 * 1024 ** 3  # 4 GB
    mock_mem.percent = 50.0
    monkeypatch.setattr(psutil, "virtual_memory", MagicMock(return_value=mock_mem))


# --- Tests ---

def test_kill_local_process_success(mock_subprocess_run):
    """Verify kill_local_process constructs and calls the correct 'kill' command."""
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    input_data = KillProcessInput(pid=1234)
    result = kill_local_process(input_data)

    mock_subprocess_run.assert_called_once_with(
        ["kill", "-9", "1234"], capture_output=True, text=True, timeout=5, check=False
    )
    assert "Successfully killed process 1234" in result


def test_run_local_command_captures_output(mock_subprocess_run):
    """Verify run_local_command correctly returns stdout and stderr."""
    mock_subprocess_run.return_value = MagicMock(
        returncode=0,
        stdout="standard output",
        stderr="standard error"
    )
    input_data = RunLocalCommandInput(command="ls -l")
    result = run_local_command(input_data)

    mock_subprocess_run.assert_called_once()
    assert "standard output" in result
    assert "[STDERR]" in result
    assert "standard error" in result


def test_get_local_memory_info(mock_psutil_memory):
    """Verify get_local_memory_info correctly formats psutil output."""
    result = get_local_memory_info(GetLocalMemoryInfoInput())

    assert "Total: 8.00 GB" in result
    assert "Available: 4.00 GB" in result
    assert "Used: 4.00 GB (Percent: 50.0%)" in result


def test_get_random_bytes_as_hex(monkeypatch):
    """Verify get_random_bytes_as_hex correctly reads and hex-encodes data."""
    # Mock reading 4 bytes: 1, 2, 16, 255
    mock_file_content = b'\x01\x02\x10\xff'
    mock_open_func = mock_open(read_data=mock_file_content)
    monkeypatch.setattr("builtins.open", mock_open_func)

    input_data = GetRandomBytesInput(length=4)
    result = get_random_bytes_as_hex(input_data)

    mock_open_func.assert_called_once_with("/dev/random", "rb")
    assert result == "010210ff"


def test_get_random_bytes_io_error(monkeypatch):
    """Verify the tool raises ToolExecutionError on a file read failure."""
    mock_open_func = mock_open()
    mock_open_func.side_effect = IOError("Permission denied")
    monkeypatch.setattr("builtins.open", mock_open_func)

    with pytest.raises(ToolExecutionError, match="Could not read random bytes"):
        get_random_bytes_as_hex(GetRandomBytesInput(length=4))
