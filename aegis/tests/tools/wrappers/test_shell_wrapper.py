# aegis/tests/tools/wrappers/test_wrapper_shell.py
"""
Unit tests for the high-level shell wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.shell import (
    run_remote_background_command, RunRemoteBackgroundCommandInput,
    run_remote_python_snippet, RunRemotePythonSnippetInput,
    run_script_if_absent, RunScriptIfAbsentInput,
    safe_shell_execute, SafeShellInput
)


# --- Fixtures ---

@pytest.fixture
def mock_ssh_executor(monkeypatch):
    """Mocks the SSHExecutor class and its instance methods."""
    mock_instance = MagicMock()
    monkeypatch.setattr("aegis.tools.wrappers.shell.SSHExecutor", MagicMock(return_value=mock_instance))
    monkeypatch.setattr("aegis.tools.wrappers.shell.get_machine", MagicMock())
    return mock_instance


@pytest.fixture
def mock_run_local_command(monkeypatch):
    """Mocks the underlying run_local_command primitive."""
    mock = MagicMock(return_value="local command output")
    monkeypatch.setattr("aegis.tools.wrappers.shell.run_local_command", mock)
    return mock


# --- Tests ---

def test_run_remote_background_command(mock_ssh_executor):
    """Verify the command is correctly wrapped with nohup for background execution."""
    input_data = RunRemoteBackgroundCommandInput(machine_name="test-host", command="sleep 10")
    run_remote_background_command(input_data)

    mock_ssh_executor.run.assert_called_once_with("nohup sleep 10 > /dev/null 2>&1 &")


def test_run_remote_python_snippet(mock_ssh_executor):
    """Verify the Python snippet is correctly passed to python3 -c."""
    code = "import os; print(os.getcwd())"
    input_data = RunRemotePythonSnippetInput(machine_name="test-host", code=code)
    run_remote_python_snippet(input_data)

    expected_cmd = f"python3 -c '{code}'"
    mock_ssh_executor.run.assert_called_once_with(expected_cmd)


def test_run_script_if_absent_file_exists(mock_ssh_executor):
    """Verify the tool does nothing if the check_path file already exists."""
    mock_ssh_executor.check_file_exists.return_value = True

    input_data = RunScriptIfAbsentInput(
        machine_name="test-host",
        check_path="/tmp/marker",
        local_script_path="/dev/null",
        remote_script_path="/dev/null"
    )
    result = run_script_if_absent(input_data)

    mock_ssh_executor.check_file_exists.assert_called_once_with("/tmp/marker")
    mock_ssh_executor.upload.assert_not_called()
    mock_ssh_executor.run.assert_not_called()
    assert "already exists. Skipping" in result


def test_run_script_if_absent_file_missing(mock_ssh_executor):
    """Verify the tool uploads and runs the script if the check_path is missing."""
    mock_ssh_executor.check_file_exists.return_value = False
    mock_ssh_executor.upload.return_value = "Upload successful"

    input_data = RunScriptIfAbsentInput(
        machine_name="test-host",
        check_path="/tmp/marker",
        local_script_path="local.sh",
        remote_script_path="/tmp/remote.sh"
    )
    run_script_if_absent(input_data)

    mock_ssh_executor.check_file_exists.assert_called_once_with("/tmp/marker")
    mock_ssh_executor.upload.assert_called_once_with("local.sh", "/tmp/remote.sh")
    mock_ssh_executor.run.assert_called_once_with("bash '/tmp/remote.sh'")


def test_safe_shell_execute_blocks_dangerous_command(mock_run_local_command):
    """Verify the safe shell blocks a command containing 'rm -rf'."""
    input_data = SafeShellInput(command="sudo rm -rf /")
    result = safe_shell_execute(input_data)

    assert "BLOCKED" in result
    mock_run_local_command.assert_not_called()


def test_safe_shell_execute_allows_safe_command(mock_run_local_command):
    """Verify the safe shell allows a benign command and calls the primitive."""
    input_data = SafeShellInput(command="ls -la")
    result = safe_shell_execute(input_data)

    mock_run_local_command.assert_called_once()
    assert result == "local command output"
