# aegis/tests/tools/wrappers/test_shell_wrapper.py
"""
Unit tests for the high-level shell wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.shell import (
    run_remote_background_command,
    RunRemoteBackgroundCommandInput,
    run_remote_python_snippet,
    RunRemotePythonSnippetInput,
    run_script_if_absent,
    RunScriptIfAbsentInput,
)


@pytest.fixture
def mock_ssh_executor_instance(monkeypatch):
    """Mocks the SSHExecutor instance methods."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = "mocked ssh run output"
    mock_instance.upload.return_value = "mocked ssh upload success"
    mock_instance.check_file_exists.return_value = (
        False  # Default to file not existing for run_script_if_absent
    )

    mock_ssh_executor_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aegis.tools.wrappers.shell.SSHExecutor", mock_ssh_executor_class
    )
    monkeypatch.setattr("aegis.tools.wrappers.shell.get_machine", MagicMock())
    return mock_instance


def test_run_remote_background_command_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = ""  # nohup command is usually silent
    input_data = RunRemoteBackgroundCommandInput(
        machine_name="test-host", command="long_script.sh --daemon"
    )
    result = run_remote_background_command(input_data)

    mock_ssh_executor_instance.run.assert_called_once_with(
        "nohup long_script.sh --daemon > /dev/null 2>&1 &"
    )
    assert (
        result
        == "Successfully launched background command on test-host: long_script.sh --daemon"
    )


def test_run_script_if_absent_file_missing_and_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = (
        False  # File does not exist
    )
    mock_ssh_executor_instance.upload.return_value = (
        "Successfully uploaded local.sh to /tmp/remote.sh"
    )
    mock_ssh_executor_instance.run.return_value = (
        "Script executed successfully, output here."
    )

    input_data = RunScriptIfAbsentInput(
        machine_name="test-host",
        check_path="/tmp/install.marker",
        local_script_path="local.sh",
        remote_script_path="/tmp/remote.sh",
    )
    result = run_script_if_absent(input_data)

    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/tmp/install.marker"
    )
    mock_ssh_executor_instance.upload.assert_called_once_with(
        "local.sh", "/tmp/remote.sh"
    )
    mock_ssh_executor_instance.run.assert_called_once_with("bash '/tmp/remote.sh'")
    assert result == "Script executed successfully, output here."
