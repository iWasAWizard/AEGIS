# aegis/tests/tools/wrappers/test_system_wrapper.py
"""
Unit tests for the high-level system wrapper tools.
"""
from unittest.mock import MagicMock, patch

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.wrapper_system import (
    get_remote_memory_info,
    MachineTargetInput,
    get_remote_hostname,
    get_remote_os_version,
    get_remote_ip_addresses,
    check_logged_in_users,
    get_last_login_times,
    get_remote_system_info,
    check_remote_processes,
    check_remote_memory_usage,
    check_remote_cpu_load,
    check_remote_service_status,
    RemoteServiceInput,
    create_remote_user,
    MachineUserInput,
    lock_remote_user_account,
    add_user_to_group,
    RemoteUserGroupInput,
)


@pytest.fixture
def mock_ssh_executor_instance(monkeypatch):
    """Mocks the SSHExecutor instance methods."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = "default mocked command output"

    mock_ssh_executor_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aegis.tools.wrappers.wrapper_system.SSHExecutor", mock_ssh_executor_class
    )
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_system.get_machine", MagicMock())
    return mock_instance


# --- Tests for simple command execution tools ---


@pytest.mark.parametrize(
    "tool_function, expected_command_executed, is_custom_message_tool",
    [
        (get_remote_memory_info, "free -h", False),
        (get_remote_hostname, "hostname", False),
        (get_remote_os_version, "cat /etc/os-release", False),
        (get_remote_ip_addresses, "hostname -I", False),
        (check_logged_in_users, "who", False),
        (get_last_login_times, "last -a", False),
        (get_remote_system_info, "uname -a", False),
        (check_remote_processes, "ps aux", False),
        (check_remote_memory_usage, "free -h", False),
        (check_remote_cpu_load, "top -bn1 | head -n 15", False),
    ],
)
def test_simple_remote_commands_success(
    mock_ssh_executor_instance,
    tool_function,
    expected_command_executed,
    is_custom_message_tool,
):
    """Verify simple tools call SSHExecutor.run and return its output."""
    mock_output = f"output from {expected_command_executed}"
    mock_ssh_executor_instance.run.return_value = mock_output

    input_data = MachineTargetInput(machine_name="test-host")
    result = tool_function(input_data)

    mock_ssh_executor_instance.run.assert_called_with(expected_command_executed)
    # For these simple tools, they directly return the executor's output
    assert result == mock_output


@pytest.mark.parametrize(
    "tool_function, expected_command_executed",
    [
        (get_remote_memory_info, "free -h"),
        (get_remote_hostname, "hostname"),
        # Add other simple tools here
    ],
)
def test_simple_remote_commands_failure(
    mock_ssh_executor_instance, tool_function, expected_command_executed
):
    """Verify simple tools propagate ToolExecutionError from SSHExecutor.run."""
    error_message = f"Remote execution of '{expected_command_executed}' failed badly."
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(error_message)

    input_data = MachineTargetInput(machine_name="test-host")
    with pytest.raises(ToolExecutionError, match=error_message):
        tool_function(input_data)
    mock_ssh_executor_instance.run.assert_called_with(expected_command_executed)


# --- Tests for tools with specific command construction or custom success messages ---


def test_check_remote_service_status_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = "nginx is active and running"
    input_data = RemoteServiceInput(machine_name="test-host", service_name="nginx")
    result = check_remote_service_status(input_data)
    mock_ssh_executor_instance.run.assert_called_with("systemctl status nginx")
    assert result == "nginx is active and running"  # Returns direct output


def test_check_remote_service_status_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "systemctl command error"
    )
    input_data = RemoteServiceInput(machine_name="test-host", service_name="nginx")
    with pytest.raises(ToolExecutionError, match="systemctl command error"):
        check_remote_service_status(input_data)
    mock_ssh_executor_instance.run.assert_called_with("systemctl status nginx")


def test_create_remote_user_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = ""  # useradd is silent
    input_data = MachineUserInput(machine_name="host1", username="john.doe")
    result = create_remote_user(input_data)
    mock_ssh_executor_instance.run.assert_called_with("sudo useradd -m john.doe")
    assert (
        result
        == "User 'john.doe' created successfully on host1 (if not already existing)."
    )


def test_create_remote_user_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "useradd execution failed"
    )
    input_data = MachineUserInput(machine_name="host1", username="john.doe")
    with pytest.raises(ToolExecutionError, match="useradd execution failed"):
        create_remote_user(input_data)


def test_lock_remote_user_account_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = ""  # passwd -l is silent
    input_data = MachineUserInput(machine_name="secure-server", username="risky_user")
    result = lock_remote_user_account(input_data)
    mock_ssh_executor_instance.run.assert_called_with("sudo passwd -l risky_user")
    assert result == "Account for user 'risky_user' locked on secure-server."


def test_lock_remote_user_account_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "passwd -l execution failed"
    )
    input_data = MachineUserInput(machine_name="secure-server", username="risky_user")
    with pytest.raises(ToolExecutionError, match="passwd -l execution failed"):
        lock_remote_user_account(input_data)


def test_add_user_to_group_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = ""  # usermod -aG is silent
    input_data = RemoteUserGroupInput(
        machine_name="dev-box", username="new_dev", group="docker"
    )
    result = add_user_to_group(input_data)
    mock_ssh_executor_instance.run.assert_called_with("sudo usermod -aG docker new_dev")
    assert result == "User 'new_dev' added to group 'docker' on dev-box."


def test_add_user_to_group_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "usermod execution failed"
    )
    input_data = RemoteUserGroupInput(
        machine_name="dev-box", username="new_dev", group="docker"
    )
    with pytest.raises(ToolExecutionError, match="usermod execution failed"):
        add_user_to_group(input_data)
