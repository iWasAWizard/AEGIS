# aegis/tests/tools/wrappers/test_filesystem_wrapper.py
"""
Unit tests for the high-level filesystem wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.wrapper_filesystem import (
    check_and_read_config_file, MachineFileInput,
    backup_remote_file, BackupRemoteFileInput,
    inject_line_into_config, InjectLineIntoConfigInput,
    diff_remote_file_after_edit, DiffRemoteFileAfterEditInput
)


# --- Fixtures ---

@pytest.fixture
def mock_ssh_executor(monkeypatch):
    """Mocks the SSHExecutor class and its instance methods."""
    mock_executor_instance = MagicMock()
    # Configure the mock to return itself from the constructor
    mock_executor_class = MagicMock(return_value=mock_executor_instance)

    # Patch the SSHExecutor class in the module where it's used
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_filesystem.SSHExecutor", mock_executor_class)

    # Also need to mock get_machine to avoid it trying to load real machines
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_filesystem.get_machine", MagicMock())

    return mock_executor_instance


# --- Tests ---

def test_check_and_read_config_file_exists(mock_ssh_executor):
    """Verify it reads the file if it exists."""
    mock_ssh_executor.check_file_exists.return_value = True
    mock_ssh_executor.run.return_value = "file content"

    input_data = MachineFileInput(machine_name="test-host", file_path="/etc/config")
    result = check_and_read_config_file(input_data)

    mock_ssh_executor.check_file_exists.assert_called_once_with("/etc/config")
    mock_ssh_executor.run.assert_called_once_with("cat '/etc/config'")
    assert result == "file content"


def test_check_and_read_config_file_missing(mock_ssh_executor):
    """Verify it returns an info message if the file is missing."""
    mock_ssh_executor.check_file_exists.return_value = False

    input_data = MachineFileInput(machine_name="test-host", file_path="/etc/config")
    result = check_and_read_config_file(input_data)

    mock_ssh_executor.check_file_exists.assert_called_once_with("/etc/config")
    mock_ssh_executor.run.assert_not_called()
    assert "[INFO] File does not exist" in result


def test_backup_remote_file(mock_ssh_executor):
    """Verify it constructs the correct 'cp' command for backup."""
    mock_ssh_executor.check_file_exists.return_value = True

    input_data = BackupRemoteFileInput(machine_name="test-host", file_path="/important/file")
    backup_remote_file(input_data)

    mock_ssh_executor.run.assert_called_once_with("sudo cp '/important/file' '/important/file.bak'")


def test_inject_line_into_config(mock_ssh_executor):
    """Verify it constructs the correct 'echo | sudo tee' command."""
    input_data = InjectLineIntoConfigInput(
        machine_name="test-host",
        file_path="/etc/sshd_config",
        line="PermitRootLogin no"
    )
    inject_line_into_config(input_data)

    expected_cmd = "echo 'PermitRootLogin no' | sudo tee -a '/etc/sshd_config'"
    mock_ssh_executor.run.assert_called_once_with(expected_cmd)


def test_diff_remote_file_after_edit(mock_ssh_executor):
    """Verify it correctly reads, writes, and diffs a remote file."""
    original_content = "key = value1"
    new_content = "key = value2"

    # Simulate two calls to run: first reads, second writes.
    mock_ssh_executor.run.side_effect = [
        original_content,  # Result of 'cat'
        "success"  # Result of 'tee'
    ]

    input_data = DiffRemoteFileAfterEditInput(
        machine_name="test-host",
        file_path="/app/config.ini",
        new_contents=new_content
    )

    result = diff_remote_file_after_edit(input_data)

    assert mock_ssh_executor.run.call_count == 2
    # Check that the diff output is correct
    assert "-key = value1" in result
    assert "+key = value2" in result
