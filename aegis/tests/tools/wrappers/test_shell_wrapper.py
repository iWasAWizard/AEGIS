# aegis/tests/tools/wrappers/test_shell_wrapper.py
"""
Unit tests for the high-level shell wrapper tools.
"""
from unittest.mock import MagicMock, patch

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.shell import (
    run_remote_background_command,
    RunRemoteBackgroundCommandInput,
    run_remote_python_snippet,
    RunRemotePythonSnippetInput,
    run_script_if_absent,
    RunScriptIfAbsentInput,
    safe_shell_execute,
    SafeShellInput,
)
from aegis.tools.primitives.primitive_system import RunLocalCommandInput


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


@pytest.fixture
def mock_run_local_command_primitive(monkeypatch):
    """Mocks the run_local_command primitive used by safe_shell_execute."""
    mock = MagicMock(return_value="local command output from primitive")
    monkeypatch.setattr("aegis.tools.wrappers.shell.run_local_command", mock)
    return mock


# --- Tests ---


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


def test_run_remote_background_command_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Failed to execute nohup"
    )
    input_data = RunRemoteBackgroundCommandInput(
        machine_name="test-host", command="failing_daemon"
    )
    with pytest.raises(ToolExecutionError, match="Failed to execute nohup"):
        run_remote_background_command(input_data)
    mock_ssh_executor_instance.run.assert_called_once_with(
        "nohup failing_daemon > /dev/null 2>&1 &"
    )


def test_run_remote_python_snippet_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = "Python output: /current/dir"
    code = "import os; print(os.getcwd())"
    input_data = RunRemotePythonSnippetInput(machine_name="test-host", code=code)
    result = run_remote_python_snippet(input_data)

    # shlex.quote is used in the tool
    expected_cmd = f"python3 -c '{code}'"
    mock_ssh_executor_instance.run.assert_called_once_with(expected_cmd)
    assert result == "Python output: /current/dir"


def test_run_remote_python_snippet_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Remote python execution failed"
    )
    code = "1/0"  # This will fail
    input_data = RunRemotePythonSnippetInput(machine_name="test-host", code=code)
    with pytest.raises(ToolExecutionError, match="Remote python execution failed"):
        run_remote_python_snippet(input_data)
    expected_cmd = f"python3 -c '{code}'"
    mock_ssh_executor_instance.run.assert_called_once_with(expected_cmd)


def test_run_script_if_absent_file_exists(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = True  # File exists

    input_data = RunScriptIfAbsentInput(
        machine_name="test-host",
        check_path="/opt/already_done.marker",
        local_script_path="setup.sh",
        remote_script_path="/tmp/setup.sh",
    )
    result = run_script_if_absent(input_data)

    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/opt/already_done.marker"
    )
    mock_ssh_executor_instance.upload.assert_not_called()
    mock_ssh_executor_instance.run.assert_not_called()
    assert (
        "[INFO] File /opt/already_done.marker already exists. Skipping script."
        in result
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


def test_run_script_if_absent_upload_fails(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = False
    mock_ssh_executor_instance.upload.side_effect = ToolExecutionError(
        "SCP permission denied for script"
    )

    input_data = RunScriptIfAbsentInput(
        machine_name="test-host",
        check_path="/tmp/marker",
        local_script_path="local.sh",
        remote_script_path="/tmp/remote.sh",
    )
    with pytest.raises(ToolExecutionError, match="SCP permission denied for script"):
        run_script_if_absent(input_data)
    mock_ssh_executor_instance.check_file_exists.assert_called_once_with("/tmp/marker")
    mock_ssh_executor_instance.upload.assert_called_once_with(
        "local.sh", "/tmp/remote.sh"
    )
    mock_ssh_executor_instance.run.assert_not_called()


def test_run_script_if_absent_script_execution_fails(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = False
    mock_ssh_executor_instance.upload.return_value = (
        "Upload successful"  # Upload succeeds
    )
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Remote bash script failed"
    )  # Run fails

    input_data = RunScriptIfAbsentInput(
        machine_name="test-host",
        check_path="/tmp/marker",
        local_script_path="local.sh",
        remote_script_path="/tmp/remote.sh",
    )
    with pytest.raises(ToolExecutionError, match="Remote bash script failed"):
        run_script_if_absent(input_data)
    mock_ssh_executor_instance.check_file_exists.assert_called_once_with("/tmp/marker")
    mock_ssh_executor_instance.upload.assert_called_once_with(
        "local.sh", "/tmp/remote.sh"
    )
    mock_ssh_executor_instance.run.assert_called_once_with("bash '/tmp/remote.sh'")


def test_safe_shell_execute_blocks_dangerous_command(mock_run_local_command_primitive):
    input_data = SafeShellInput(
        command="sudo rm -rf /some/path"
    )  # Example dangerous command
    result = safe_shell_execute(input_data)
    assert "[BLOCKED] Command contains potentially dangerous operations." in result
    mock_run_local_command_primitive.assert_not_called()


def test_safe_shell_execute_allows_safe_command_and_success(
    mock_run_local_command_primitive,
):
    mock_run_local_command_primitive.return_value = "safe command output"
    input_data = SafeShellInput(command="echo 'hello'")
    result = safe_shell_execute(input_data)

    mock_run_local_command_primitive.assert_called_once()
    call_arg_input = mock_run_local_command_primitive.call_args[0][0]
    assert isinstance(call_arg_input, RunLocalCommandInput)
    assert call_arg_input.command == "echo 'hello'"
    assert call_arg_input.shell is True
    assert result == "safe command output"


def test_safe_shell_execute_primitive_call_fails(mock_run_local_command_primitive):
    mock_run_local_command_primitive.side_effect = ToolExecutionError(
        "Local primitive execution failed"
    )
    input_data = SafeShellInput(command="a_safe_command_that_will_fail_in_primitive")

    with pytest.raises(ToolExecutionError, match="Local primitive execution failed"):
        safe_shell_execute(input_data)
    mock_run_local_command_primitive.assert_called_once()
