# aegis/tests/tools/primitives/test_system_primitive.py
"""
Unit tests for the local system primitive tools.
"""
import subprocess
from unittest.mock import MagicMock, mock_open

import psutil  # type: ignore
import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.primitives.primitive_system import (
    kill_local_process,
    KillProcessInput,
    run_local_command,
    RunLocalCommandInput,
    get_local_memory_info,
    GetLocalMemoryInfoInput,
    get_random_bytes_as_hex,
    GetRandomBytesInput,
)


@pytest.fixture
def mock_subprocess_run_for_kill(monkeypatch):
    """Fixture to mock subprocess.run specifically for kill_local_process."""
    mock = MagicMock()
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


@pytest.fixture
def mock_local_executor_run(monkeypatch):
    """Fixture to mock LocalExecutor's run method."""
    mock_run_method = MagicMock(return_value="mocked local command output")
    # Patch the run method of the LocalExecutor class globally for tests in this module
    # This assumes LocalExecutor is instantiated fresh in the tool.
    # If LocalExecutor was a singleton or passed around, a different mock strategy might be needed.
    monkeypatch.setattr("aegis.executors.local.LocalExecutor.run", mock_run_method)
    return mock_run_method


@pytest.fixture
def mock_psutil_memory(monkeypatch):
    """Fixture to mock psutil.virtual_memory."""
    mock_mem = MagicMock()
    mock_mem.total = 8 * 1024**3
    mock_mem.available = 4 * 1024**3
    mock_mem.used = 4 * 1024**3
    mock_mem.percent = 50.0
    monkeypatch.setattr(psutil, "virtual_memory", MagicMock(return_value=mock_mem))


# --- Tests ---


def test_kill_local_process_success(mock_subprocess_run_for_kill):
    """Verify kill_local_process constructs and calls the correct 'kill' command."""
    mock_subprocess_run_for_kill.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )
    input_data = KillProcessInput(pid=1234)
    result = kill_local_process(input_data)

    mock_subprocess_run_for_kill.assert_called_once_with(
        ["kill", "-9", "1234"], capture_output=True, text=True, timeout=5, check=False
    )
    assert "Successfully killed process 1234" in result


def test_kill_local_process_failure_rc(mock_subprocess_run_for_kill):
    """Verify kill_local_process raises ToolExecutionError on non-zero return code."""
    mock_subprocess_run_for_kill.return_value = MagicMock(
        returncode=1, stdout="", stderr="No such process"
    )
    input_data = KillProcessInput(pid=1234)
    with pytest.raises(
        ToolExecutionError,
        match="Kill command failed for PID 1234 with RC 1. Error: No such process",
    ):
        kill_local_process(input_data)


def test_kill_local_process_timeout(mock_subprocess_run_for_kill):
    """Verify kill_local_process raises ToolExecutionError on timeout."""
    mock_subprocess_run_for_kill.side_effect = subprocess.TimeoutExpired("kill", 5)
    input_data = KillProcessInput(pid=1234)
    with pytest.raises(
        ToolExecutionError, match="Kill command for PID 1234 timed out."
    ):
        kill_local_process(input_data)


def test_kill_local_process_not_found(mock_subprocess_run_for_kill):
    """Verify kill_local_process raises ToolExecutionError if 'kill' command is not found."""
    mock_subprocess_run_for_kill.side_effect = FileNotFoundError
    input_data = KillProcessInput(pid=1234)
    with pytest.raises(
        ToolExecutionError,
        match="'kill' command not found. Is it installed and in PATH?",
    ):
        kill_local_process(input_data)


def test_run_local_command_success(mock_local_executor_run):
    """Verify run_local_command calls LocalExecutor.run and returns its output."""
    input_data = RunLocalCommandInput(command="ls -l", shell=True, timeout=30)
    result = run_local_command(input_data)

    mock_local_executor_run.assert_called_once_with(
        command="ls -l", shell=True, timeout=30
    )
    assert result == "mocked local command output"


def test_run_local_command_failure_propagates(mock_local_executor_run):
    """Verify ToolExecutionError from LocalExecutor.run propagates."""
    mock_local_executor_run.side_effect = ToolExecutionError(
        "Executor failed for local command"
    )
    input_data = RunLocalCommandInput(command="failing_cmd")

    with pytest.raises(ToolExecutionError, match="Executor failed for local command"):
        run_local_command(input_data)


def test_get_local_memory_info(mock_psutil_memory):
    """Verify get_local_memory_info correctly formats psutil output."""
    result = get_local_memory_info(GetLocalMemoryInfoInput())

    assert "Total: 8.00 GB" in result
    assert "Available: 4.00 GB" in result
    assert "Used: 4.00 GB (Percent: 50.0%)" in result


def test_get_local_memory_info_psutil_error(monkeypatch):
    """Verify get_local_memory_info raises ToolExecutionError if psutil fails."""
    monkeypatch.setattr(
        psutil,
        "virtual_memory",
        MagicMock(side_effect=psutil.Error("psutil general error")),
    )
    with pytest.raises(
        ToolExecutionError,
        match="Could not retrieve memory info. psutil might be missing or failed: psutil general error",
    ):
        get_local_memory_info(GetLocalMemoryInfoInput())


def test_get_random_bytes_as_hex(monkeypatch):
    """Verify get_random_bytes_as_hex correctly reads and hex-encodes data."""
    mock_file_content = b"\x01\x02\x10\xff"
    mock_open_func = mock_open(read_data=mock_file_content)
    monkeypatch.setattr("builtins.open", mock_open_func)

    input_data = GetRandomBytesInput(length=4)
    result = get_random_bytes_as_hex(input_data)

    mock_open_func.assert_called_once_with("/dev/random", "rb")
    assert result == "010210ff"


def test_get_random_bytes_file_not_found(monkeypatch):
    """Verify get_random_bytes_as_hex raises ToolExecutionError if /dev/random not found."""
    mock_open_func = mock_open()
    mock_open_func.side_effect = FileNotFoundError
    monkeypatch.setattr("builtins.open", mock_open_func)

    with pytest.raises(
        ToolExecutionError, match="Could not read random bytes: /dev/random not found."
    ):
        get_random_bytes_as_hex(GetRandomBytesInput(length=4))


def test_get_random_bytes_io_error(monkeypatch):
    """Verify get_random_bytes_as_hex raises ToolExecutionError on other IOErrors."""
    mock_open_func = mock_open()
    mock_open_func.side_effect = IOError("Permission denied to /dev/random")
    monkeypatch.setattr("builtins.open", mock_open_func)

    with pytest.raises(
        ToolExecutionError,
        match="Could not read random bytes: Permission denied to /dev/random",
    ):
        get_random_bytes_as_hex(GetRandomBytesInput(length=4))
