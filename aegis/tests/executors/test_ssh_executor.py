# aegis/tests/executors/test_ssh_executor.py
"""
Unit tests for the SSHExecutor class.
"""
import subprocess
from unittest.mock import MagicMock

import pytest

from aegis.executors.ssh import SSHExecutor
from aegis.schemas.machine import MachineManifest


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Fixture to mock subprocess.run and prevent actual network calls."""
    mock = MagicMock()
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


@pytest.fixture
def sample_machine() -> MachineManifest:
    """Provides a sample MachineManifest object for tests."""
    return MachineManifest(
        name="testhost",
        ip="127.0.0.1",
        platform="linux",
        provider="test",
        type="vm",
        shell="bash",
        username="testuser",
        password="password",
        ssh_port=2222,
    )


def test_ssh_executor_run_command_success(mock_subprocess_run, sample_machine):
    """Verify that run() constructs a valid SSH command and returns stdout on success."""
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout="success", stderr=""
    )
    executor = SSHExecutor(sample_machine)
    result = executor.run("ls -la /tmp")

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
        "testuser@127.0.0.1",
        "ls -la /tmp",
    ]
    assert call_args == expected_cmd
    assert result == "success"


def test_run_handles_stderr(mock_subprocess_run, sample_machine):
    """Verify that stderr from the remote command is correctly appended."""
    mock_subprocess_run.return_value = MagicMock(
        returncode=1, stdout="some output", stderr="permission denied"
    )
    executor = SSHExecutor(sample_machine)
    result = executor.run("cat /root/secret")

    assert "some output" in result
    assert "[STDERR]" in result
    assert "permission denied" in result


def test_ssh_executor_upload_command(mock_subprocess_run, sample_machine):
    """Verify that upload() constructs a valid SCP command."""
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    executor = SSHExecutor(sample_machine)
    executor.upload("/local/file", "/remote/file")

    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    expected_cmd = [
        "scp",
        "-P",
        "2222",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "/local/file",
        "testuser@127.0.0.1:/remote/file",
    ]
    assert call_args == expected_cmd


def test_ssh_executor_download_command(mock_subprocess_run, sample_machine):
    """Verify that download() constructs a valid SCP command."""
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    executor = SSHExecutor(sample_machine)
    executor.download("/remote/file", "/local/file")

    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    expected_cmd = [
        "scp",
        "-P",
        "2222",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "testuser@127.0.0.1:/remote/file",
        "/local/file",
    ]
    assert call_args == expected_cmd


def test_upload_and_download_failure(mock_subprocess_run, sample_machine):
    """Verify that upload/download methods return an error string on failure."""
    mock_subprocess_run.return_value = MagicMock(
        returncode=1, stdout="", stderr="No such file or directory"
    )
    executor = SSHExecutor(sample_machine)

    upload_result = executor.upload("/bad/path", "/remote/path")
    assert "[ERROR] SCP upload failed" in upload_result
    assert "No such file or directory" in upload_result

    download_result = executor.download("/bad/remote", "/local")
    assert "[ERROR] SCP download failed" in download_result
    assert "No such file or directory" in download_result


def test_check_file_exists_positive_and_negative(mock_subprocess_run, sample_machine):
    """Verify check_file_exists handles both found and not-found cases."""
    executor = SSHExecutor(sample_machine)

    # Case 1: File exists
    mock_subprocess_run.return_value = MagicMock(
        returncode=0, stdout="AEGIS_FILE_EXISTS", stderr=""
    )
    assert executor.check_file_exists("/path/to/file.txt") is True

    # Check that the correct command was used
    mock_subprocess_run.assert_called_once_with(
        [
            "ssh",
            "-p",
            "2222",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "testuser@127.0.0.1",
            "test -f '/path/to/file.txt' && echo 'AEGIS_FILE_EXISTS'",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    # Case 2: File does not exist (command fails with returncode 1, stdout is empty)
    mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
    assert executor.check_file_exists("/path/to/other.txt") is False
