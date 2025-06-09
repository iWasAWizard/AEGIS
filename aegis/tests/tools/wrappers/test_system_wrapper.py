# aegis/tests/tools/wrappers/test_system_wrapper.py
"""
Unit tests for the high-level system wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.wrapper_system import (
    get_remote_memory_info, MachineTargetInput,
    get_remote_hostname,
    get_remote_os_version,
    get_remote_ip_addresses,
    check_logged_in_users,
    get_last_login_times,
    get_remote_system_info,
    check_remote_processes,
    check_remote_memory_usage,
    check_remote_cpu_load,
    check_remote_service_status, RemoteServiceInput,
    create_remote_user, MachineUserInput,
    lock_remote_user_account,
    add_user_to_group, RemoteUserGroupInput,
)


# --- Fixtures ---

@pytest.fixture
def mock_ssh_executor(monkeypatch):
    """Mocks the SSHExecutor class and its instance methods."""
    mock_instance = MagicMock()
    mock_executor_class = MagicMock(return_value=mock_instance)

    monkeypatch.setattr("aegis.tools.wrappers.wrapper_system.SSHExecutor", mock_executor_class)
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_system.get_machine", MagicMock())

    return mock_instance


# --- Tests ---

@pytest.mark.parametrize("tool_function, expected_command", [
    (get_remote_memory_info, "free -h"),
    (get_remote_hostname, "hostname"),
    (get_remote_os_version, "cat /etc/os-release"),
    (get_remote_ip_addresses, "hostname -I"),
    (check_logged_in_users, "who"),
    (get_last_login_times, "last -a"),
    (get_remote_system_info, "uname -a"),
    (check_remote_processes, "ps aux"),
    (check_remote_memory_usage, "free -h"),
    (check_remote_cpu_load, "top -bn1 | head -n 15"),
])
def test_simple_remote_commands(mock_ssh_executor, tool_function, expected_command):
    """Verify that simple, no-argument tools call the correct shell command."""
    input_data = MachineTargetInput(machine_name="test-host")
    tool_function(input_data)
    mock_ssh_executor.run.assert_called_with(expected_command)


def test_check_remote_service_status(mock_ssh_executor):
    """Verify service status command includes the service name."""
    input_data = RemoteServiceInput(machine_name="test-host", service_name="nginx")
    check_remote_service_status(input_data)
    mock_ssh_executor.run.assert_called_with("systemctl status nginx")


def test_create_remote_user(mock_ssh_executor):
    """Verify create user command includes the username."""
    input_data = MachineUserInput(machine_name="test-host", username="newuser")
    create_remote_user(input_data)
    mock_ssh_executor.run.assert_called_with("sudo useradd -m newuser")


def test_lock_remote_user_account(mock_ssh_executor):
    """Verify lock account command includes the username."""
    input_data = MachineUserInput(machine_name="test-host", username="baduser")
    lock_remote_user_account(input_data)
    mock_ssh_executor.run.assert_called_with("sudo passwd -l baduser")


def test_add_user_to_group(mock_ssh_executor):
    """Verify add user to group command includes both username and group."""
    input_data = RemoteUserGroupInput(machine_name="test-host", username="testuser", group="sudo")
    add_user_to_group(input_data)
    mock_ssh_executor.run.assert_called_with("sudo usermod -aG sudo testuser")
