# aegis/tests/executors/test_ssh_executor.py
"""
Unit tests for the SSHExecutor class.
"""
import subprocess
from unittest.mock import MagicMock

import pytest

from aegis.executors.ssh import SSHExecutor


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Fixture to mock subprocess.run and prevent actual network calls."""
    mock = MagicMock()
    # Default return value for a successful command
    mock.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="success", stderr=""
    )
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


def test_ssh_executor_run_command(mock_subprocess_run):
    """Verify that run() constructs a valid SSH command."""
    executor = SSHExecutor(host="testhost", user="testuser", port=2222)
    result = executor.run("ls -la /tmp")

    # Check that subprocess.run was called with the correct command list
    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    expected_cmd = [
        "ssh",
        "-p",
        "2222",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "testuser@testhost",
        "ls -la /tmp",
    ]
    assert call_args == expected_cmd
    assert result == "success"


def test_ssh_executor_upload_command(mock_subprocess_run):
    """Verify that upload() constructs a valid SCP command."""
    executor = SSHExecutor(host="testhost", user="testuser", ssh_key_path="/tmp/key")
    executor.upload("/local/file", "/remote/file")

    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    expected_cmd = [
        "scp",
        "-P",
        "22",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-i",
        "/tmp/key",
        "/local/file",
        "testuser@testhost:/remote/file",
    ]
    assert call_args == expected_cmd


def test_ssh_executor_download_command(mock_subprocess_run):
    """Verify that download() constructs a valid SCP command."""
    executor = SSHExecutor(host="testhost", user="testuser")
    executor.download("/remote/file", "/local/file")

    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    expected_cmd = [
        "scp",
        "-P",
        "22",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "testuser@testhost:/remote/file",
        "/local/file",
    ]
    assert call_args == expected_cmd


def test_ssh_executor_check_file_exists_command(mock_subprocess_run):
    """Verify the specific and reliable command used for checking file existence."""
    executor = SSHExecutor(host="testhost", user="testuser")
    executor.check_file_exists("/path/to/file.txt")

    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    # Note the use of shlex.quote in the implementation, so we check for the quoted path
    assert call_args[-1] == "test -f '/path/to/file.txt' && echo 'AEGIS_FILE_EXISTS'"
