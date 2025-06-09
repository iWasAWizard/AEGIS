# aegis/tools/wrappers/wrapper_system.py
"""
System wrapper tools for common OS and hardware inspection tasks.

This module provides higher-level, "canned" commands for common system
administration and monitoring tasks, such as checking memory usage, OS version,
or managing users. These tools are built on top of the SSHExecutor.
"""

from pydantic import BaseModel, Field

from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import RemoteTargetInput, RemoteUserInput
from aegis.utils.host_utils import get_user_host_from_string
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# === Input Models ===


class RemoteServiceInput(RemoteTargetInput):
    """Input model for checking a service on a remote host."""

    service_name: str = Field(
        ..., description="The name of the systemd service to check."
    )


class RemoteUserGroupInput(RemoteUserInput):
    """Input model for adding a remote user to a group."""

    group: str = Field(..., description="The group to add the user to.")


# === Tools ===


@register_tool(
    name="get_remote_memory_info",
    input_model=RemoteTargetInput,
    tags=["monitoring", "remote", "ssh", "memory"],
    description="Get memory usage from a remote system using 'free -h'.",
    safe_mode=True,
    purpose="Monitor memory usage remotely via SSH.",
    category="monitoring",
)
def get_remote_memory_info(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("free -h")


@register_tool(
    name="get_remote_hostname",
    input_model=RemoteTargetInput,
    tags=["ssh", "remote", "system", "midlevel"],
    description="Get the hostname of a remote machine.",
    safe_mode=True,
    purpose="Retrieve the hostname of the remote machine",
    category="system",
)
def get_remote_hostname(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("hostname")


@register_tool(
    name="get_remote_os_version",
    input_model=RemoteTargetInput,
    tags=["ssh", "remote", "system", "os", "midlevel"],
    description="Get OS version details from a remote machine using /etc/os-release.",
    safe_mode=True,
    purpose="Get Linux OS release information on a remote machine",
    category="system",
)
def get_remote_os_version(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("cat /etc/os-release")


@register_tool(
    name="get_remote_ip_addresses",
    input_model=RemoteTargetInput,
    tags=["ssh", "remote", "network", "ip", "midlevel"],
    description="Get the IP addresses of a remote machine.",
    safe_mode=True,
    purpose="Retrieve the IP addresses assigned to the remote machine",
    category="network",
)
def get_remote_ip_addresses(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("hostname -I")


@register_tool(
    name="check_logged_in_users",
    input_model=RemoteTargetInput,
    tags=["ssh", "remote", "users", "midlevel"],
    description="Check who is currently logged into a remote machine using 'who'.",
    safe_mode=True,
    purpose="List users currently logged into the remote system",
    category="monitoring",
)
def check_logged_in_users(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("who")


@register_tool(
    name="get_last_login_times",
    input_model=RemoteTargetInput,
    tags=["ssh", "remote", "users", "logins", "midlevel"],
    description="Get historical login data from the remote system using 'last'.",
    safe_mode=True,
    purpose="Display recent login history on the remote system",
    category="auth",
)
def get_last_login_times(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("last -a")


@register_tool(
    name="get_remote_system_info",
    input_model=RemoteTargetInput,
    tags=["remote", "system", "wrapper"],
    description="Get basic system information from a remote host using 'uname -a'.",
    safe_mode=True,
    purpose="Remotely retrieve system information like kernel, architecture, and hostname.",
    category="system",
)
def get_remote_system_info(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("uname -a")


@register_tool(
    name="check_remote_processes",
    input_model=RemoteTargetInput,
    tags=["ssh", "remote", "process", "midlevel"],
    description="Retrieve the process list from a remote machine using 'ps aux'.",
    safe_mode=True,
    purpose="Retrieve a list of running processes on a remote machine",
    category="monitoring",
)
def check_remote_processes(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("ps aux")


@register_tool(
    name="check_remote_memory_usage",
    input_model=RemoteTargetInput,
    tags=["ssh", "remote", "memory", "usage", "midlevel"],
    description="Check memory usage on a remote machine using 'free -h'.",
    safe_mode=True,
    purpose="Get memory usage statistics from the remote machine",
    category="monitoring",
)
def check_remote_memory_usage(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("free -h")


@register_tool(
    name="check_remote_cpu_load",
    input_model=RemoteTargetInput,
    tags=["ssh", "remote", "cpu", "load", "midlevel"],
    description="Get CPU load summary from a remote machine.",
    safe_mode=True,
    purpose="Check real-time CPU usage on a remote system",
    category="monitoring",
)
def check_remote_cpu_load(input_data: RemoteTargetInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run("top -bn1 | head -n 15")


@register_tool(
    name="check_remote_service_status",
    input_model=RemoteServiceInput,
    tags=["ssh", "service", "status", "midlevel"],
    description="Check status of a systemd service on a remote machine.",
    safe_mode=True,
    purpose="Check systemd service status remotely",
    category="system",
)
def check_remote_service_status(input_data: RemoteServiceInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run(f"systemctl status {input_data.service_name}")


@register_tool(
    name="create_remote_user",
    input_model=RemoteUserInput,
    tags=["ssh", "user", "create", "midlevel"],
    description="Create a user on the remote system with home directory.",
    safe_mode=True,
    purpose="Create a new user account on a remote machine",
    category="auth",
)
def create_remote_user(input_data: RemoteUserInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run(f"sudo useradd -m {input_data.username}")


@register_tool(
    name="lock_remote_user_account",
    category="auth",
    input_model=RemoteUserInput,
    tags=["ssh", "user", "lock", "midlevel"],
    description="Lock a user account on the remote host (passwd -l).",
    safe_mode=True,
    purpose="Lock a user account on a remote host",
)
def lock_remote_user_account(input_data: RemoteUserInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run(f"sudo passwd -l {input_data.username}")


@register_tool(
    name="add_user_to_group",
    input_model=RemoteUserGroupInput,
    tags=["ssh", "user", "group", "midlevel"],
    description="Add a user to a group on the remote system.",
    safe_mode=True,
    purpose="Add a user to a group on the remote machine",
    category="auth",
)
def add_user_to_group(input_data: RemoteUserGroupInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run(f"sudo usermod -aG {input_data.group} {input_data.username}")
