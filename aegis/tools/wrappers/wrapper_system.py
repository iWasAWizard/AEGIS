# aegis/tools/wrappers/wrapper_system.py
"""
System wrapper tools for common OS and hardware inspection tasks.

This module provides higher-level, "canned" commands for common system
administration and monitoring tasks, such as checking memory usage, OS version,
or managing users. These tools are built on top of the SSHExecutor.
"""

from pydantic import Field

from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import MachineTargetInput, MachineUserInput
from aegis.utils.logger import setup_logger
from aegis.utils.machine_loader import get_machine

logger = setup_logger(__name__)


# === Input Models ===


class RemoteServiceInput(MachineTargetInput):
    """Input model for checking a service on a remote host.

    :ivar service_name: The name of the systemd service to check.
    :vartype service_name: str
    """

    service_name: str = Field(
        ..., description="The name of the systemd service to check."
    )


class RemoteUserGroupInput(MachineUserInput):
    """Input model for adding a remote user to a group.

    :ivar group: The group to add the user to.
    :vartype group: str
    """

    group: str = Field(..., description="The group to add the user to.")


# === Tools ===


@register_tool(
    name="get_remote_memory_info",
    input_model=MachineTargetInput,
    tags=["monitoring", "remote", "ssh", "memory", "wrapper"],
    description="Get memory usage from a remote system using 'free -h'.",
    safe_mode=True,
    purpose="Monitor memory usage remotely via SSH.",
    category="monitoring",
)
def get_remote_memory_info(input_data: MachineTargetInput) -> str:
    """Gets memory usage from a remote Linux system.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'free -h' command.
    :rtype: str
    """
    logger.info(f"Getting remote memory info from {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("free -h")


@register_tool(
    name="get_remote_hostname",
    input_model=MachineTargetInput,
    tags=["ssh", "remote", "system", "wrapper"],
    description="Get the hostname of a remote machine.",
    safe_mode=True,
    purpose="Retrieve the hostname of the remote machine",
    category="system",
)
def get_remote_hostname(input_data: MachineTargetInput) -> str:
    """Gets the hostname of a remote system.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'hostname' command.
    :rtype: str
    """
    logger.info(f"Getting remote hostname from {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("hostname")


@register_tool(
    name="get_remote_os_version",
    input_model=MachineTargetInput,
    tags=["ssh", "remote", "system", "os", "wrapper"],
    description="Get OS version details from a remote machine using /etc/os-release.",
    safe_mode=True,
    purpose="Get Linux OS release information on a remote machine",
    category="system",
)
def get_remote_os_version(input_data: MachineTargetInput) -> str:
    """Gets OS version from a remote Linux system.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The contents of the '/etc/os-release' file.
    :rtype: str
    """
    logger.info(f"Getting remote OS version from {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("cat /etc/os-release")


@register_tool(
    name="get_remote_ip_addresses",
    input_model=MachineTargetInput,
    tags=["ssh", "remote", "network", "ip", "wrapper"],
    description="Get the IP addresses of a remote machine.",
    safe_mode=True,
    purpose="Retrieve the IP addresses assigned to the remote machine",
    category="network",
)
def get_remote_ip_addresses(input_data: MachineTargetInput) -> str:
    """Gets IP addresses from a remote Linux system.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'hostname -I' command.
    :rtype: str
    """
    logger.info(f"Getting remote IP addresses from {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("hostname -I")


@register_tool(
    name="check_logged_in_users",
    input_model=MachineTargetInput,
    tags=["ssh", "remote", "users", "wrapper"],
    description="Check who is currently logged into a remote machine using 'who'.",
    safe_mode=True,
    purpose="List users currently logged into the remote system",
    category="monitoring",
)
def check_logged_in_users(input_data: MachineTargetInput) -> str:
    """Checks for currently logged-in users on a remote system.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'who' command.
    :rtype: str
    """
    logger.info(f"Checking logged in users on {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("who")


@register_tool(
    name="get_last_login_times",
    input_model=MachineTargetInput,
    tags=["ssh", "remote", "users", "logins", "wrapper"],
    description="Get historical login data from the remote system using 'last'.",
    safe_mode=True,
    purpose="Display recent login history on the remote system",
    category="auth",
)
def get_last_login_times(input_data: MachineTargetInput) -> str:
    """Gets recent login history from a remote system.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'last -a' command.
    :rtype: str
    """
    logger.info(f"Getting last login times from {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("last -a")


@register_tool(
    name="get_remote_system_info",
    input_model=MachineTargetInput,
    tags=["remote", "system", "wrapper"],
    description="Get basic system information from a remote host using 'uname -a'.",
    safe_mode=True,
    purpose="Remotely retrieve system information like kernel, architecture, and hostname.",
    category="system",
)
def get_remote_system_info(input_data: MachineTargetInput) -> str:
    """Gets basic system information from a remote host.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'uname -a' command.
    :rtype: str
    """
    logger.info(f"Getting remote system info from {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("uname -a")


@register_tool(
    name="check_remote_processes",
    input_model=MachineTargetInput,
    tags=["ssh", "remote", "process", "wrapper"],
    description="Retrieve the process list from a remote machine using 'ps aux'.",
    safe_mode=True,
    purpose="Retrieve a list of running processes on a remote machine",
    category="monitoring",
)
def check_remote_processes(input_data: MachineTargetInput) -> str:
    """Gets the process list from a remote system.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'ps aux' command.
    :rtype: str
    """
    logger.info(f"Checking remote processes on {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("ps aux")


@register_tool(
    name="check_remote_memory_usage",
    input_model=MachineTargetInput,
    tags=["ssh", "remote", "memory", "usage", "wrapper"],
    description="Check memory usage on a remote machine using 'free -h'.",
    safe_mode=True,
    purpose="Get memory usage statistics from the remote machine",
    category="monitoring",
)
def check_remote_memory_usage(input_data: MachineTargetInput) -> str:
    """Checks memory usage on a remote system.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'free -h' command.
    :rtype: str
    """
    logger.info(f"Checking remote memory usage on {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("free -h")


@register_tool(
    name="check_remote_cpu_load",
    input_model=MachineTargetInput,
    tags=["ssh", "remote", "cpu", "load", "wrapper"],
    description="Get CPU load summary from a remote machine.",
    safe_mode=True,
    purpose="Check real-time CPU usage on a remote system",
    category="monitoring",
)
def check_remote_cpu_load(input_data: MachineTargetInput) -> str:
    """Gets the current CPU load from a remote system using `top`.

    :param input_data: An object containing the machine name.
    :type input_data: MachineTargetInput
    :return: The output of the 'top' command, limited to the first 15 lines.
    :rtype: str
    """
    logger.info(f"Checking remote CPU load on {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run("top -bn1 | head -n 15")


@register_tool(
    name="check_remote_service_status",
    input_model=RemoteServiceInput,
    tags=["ssh", "service", "status", "wrapper"],
    description="Check status of a systemd service on a remote machine.",
    safe_mode=True,
    purpose="Check systemd service status remotely",
    category="system",
)
def check_remote_service_status(input_data: RemoteServiceInput) -> str:
    """Checks the status of a systemd service on a remote system.

    :param input_data: An object containing the machine name and service name.
    :type input_data: RemoteServiceInput
    :return: The output of the 'systemctl status' command.
    :rtype: str
    """
    logger.info(
        f"Checking service '{input_data.service_name}' status on {input_data.machine_name}"
    )
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run(f"systemctl status {input_data.service_name}")


@register_tool(
    name="create_remote_user",
    input_model=MachineUserInput,
    tags=["ssh", "user", "create", "wrapper"],
    description="Create a user on the remote system with home directory.",
    safe_mode=True,  # Administrative but not destructive by default
    purpose="Create a new user account on a remote machine",
    category="auth",
)
def create_remote_user(input_data: MachineUserInput) -> str:
    """Creates a new user on a remote system.

    :param input_data: An object containing the machine name and username.
    :type input_data: MachineUserInput
    :return: The output of the 'useradd' command.
    :rtype: str
    """
    logger.info(f"Creating user '{input_data.username}' on {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run(f"sudo useradd -m {input_data.username}")


@register_tool(
    name="lock_remote_user_account",
    category="auth",
    input_model=MachineUserInput,
    tags=["ssh", "user", "lock", "wrapper"],
    description="Lock a user account on the remote host (passwd -l).",
    safe_mode=True,
    purpose="Lock a user account on a remote host",
)
def lock_remote_user_account(input_data: MachineUserInput) -> str:
    """Locks a user account on a remote system.

    :param input_data: An object containing the machine name and username.
    :type input_data: MachineUserInput
    :return: The output of the 'passwd -l' command.
    :rtype: str
    """
    logger.info(f"Locking user '{input_data.username}' on {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run(f"sudo passwd -l {input_data.username}")


@register_tool(
    name="add_user_to_group",
    input_model=RemoteUserGroupInput,
    tags=["ssh", "user", "group", "wrapper"],
    description="Add a user to a group on the remote system.",
    safe_mode=True,
    purpose="Add a user to a group on the remote machine",
    category="auth",
)
def add_user_to_group(input_data: RemoteUserGroupInput) -> str:
    """Adds an existing user to a group on a remote system.

    :param input_data: An object containing the machine name, username, and group.
    :type input_data: RemoteUserGroupInput
    :return: The output of the 'usermod' command.
    :rtype: str
    """
    logger.info(
        f"Adding user '{input_data.username}' to group '{input_data.group}' on {input_data.machine_name}"
    )
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run(f"sudo usermod -aG {input_data.group} {input_data.username}")
