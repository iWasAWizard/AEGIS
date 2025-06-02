"""
System wrapper tools for combining hardware or OS insights with validation and reporting.

Aggregates primitives into more structured or multi-step inspections suitable for external analysis.
"""

import subprocess

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.tools.wrappers.shell import (
    run_remote_command,
    RunRemoteCommandInput,
    run_remote_interactive_command,
    RunRemoteInteractiveCommandInput,
)
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class GetRemoteHostnameInput(BaseModel):
    host: str
    ssh_key_path: str


class GetRemoteOSVersionInput(BaseModel):
    host: str
    ssh_key_path: str


class GetRemoteIPAddressesInput(BaseModel):
    host: str
    ssh_key_path: str


class CheckLoggedInUsersInput(BaseModel):
    host: str
    ssh_key_path: str


class GetLastLoginTimesInput(BaseModel):
    host: str
    ssh_key_path: str


class RemoteSysInfoInput(BaseModel):
    host: str
    ssh_key_path: str


class GetRemoteMemoryInfoInput(BaseModel):
    """Input for getting memory stats via SSH.

:ivar host: Remote host address.
:ivar user: Username for SSH authentication."""
    host: str = Field(description="Remote host to connect to")
    user: str = Field(description="SSH username")


class CheckRemoteMemoryUsageInput(BaseModel):
    host: str
    ssh_key_path: str


class CheckRemoteProcessesInput(BaseModel):
    host: str
    ssh_key_path: str


class CheckRemoteCPULoadInput(BaseModel):
    host: str
    ssh_key_path: str


class CheckRemoteServiceStatusInput(BaseModel):
    host: str
    service_name: str
    ssh_key_path: str


class RunRemoteBenchmarkInput(BaseModel):
    command: str
    timeout: int


class CreateRemoteUserInput(BaseModel):
    host: str = Field(description="Remote host (user@host).")
    username: str = Field(description="Username to create.")
    ssh_key_path: str = Field(description="SSH key for authentication.")


class LockRemoteUserAccountInput(BaseModel):
    host: str = Field(description="Remote host (user@host).")
    username: str = Field(description="Username to lock.")
    ssh_key_path: str = Field(description="SSH key for authentication.")


class AddUserToGroupInput(BaseModel):
    host: str = Field(description="Remote host (user@host).")
    username: str = Field(description="User to modify.")
    group: str = Field(description="Group to add the user to.")
    ssh_key_path: str = Field(description="SSH key for authentication.")


class ResetRemotePasswordInput(BaseModel):
    host: str = Field(description="Remote host (user@host).")
    username: str = Field(description="Username to reset password for.")
    ssh_key_path: str = Field(description="SSH key for authentication.")


# === Tools ===


@register_tool(
    name="get_remote_memory_info",
    input_model=GetRemoteMemoryInfoInput,
    tags=["monitoring", "remote", "ssh", "memory"],
    description="Get memory usage from a remote system using 'free -h'.",
    safe_mode=True,
    purpose="Monitor memory usage remotely via SSH.",
    category="monitoring",
)
def get_remote_memory_info(input_data: GetRemoteMemoryInfoInput) -> str:
    """Use SSH to retrieve memory statistics using the 'free -h' command.

:param input_data: Host and user credentials.
:return: Output of memory usage."""
    ssh_target = f"{input_data.user}@{input_data.host}"
    try:
        result = subprocess.run(
            ["ssh", ssh_target, "free -h"], capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[wrapper_system] Error: {e}")
        return f"[ERROR] Failed to get remote memory info: {str(e)}"


@register_tool(
    name="get_remote_hostname",
    input_model=GetRemoteHostnameInput,
    tags=["ssh", "remote", "system", "midlevel"],
    description="Get the hostname of a remote machine.",
    safe_mode=True,
    purpose="Retrieve the hostname of the remote machine",
    category="system",
)
def get_remote_hostname(input_data: GetRemoteHostnameInput) -> str:
    """Get the hostname of a remote system via SSH.

:param input_data: Connection and authentication parameters.
:return: Hostname string."""
    logger.info(
        "Fetching remote hostname",
        event_type="get_remote_hostname",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command="hostname",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="get_remote_os_version",
    input_model=GetRemoteOSVersionInput,
    tags=["ssh", "remote", "system", "os", "midlevel"],
    description="Get OS version details from a remote machine using /etc/os-release.",
    safe_mode=True,
    purpose="Get Linux OS release information on a remote machine",
    category="system",
)
def get_remote_os_version(input_data: GetRemoteOSVersionInput) -> str:
    """Get Linux OS version info by reading /etc/os-release on a remote host.

:param input_data: SSH parameters.
:return: OS version string."""
    logger.info(
        "Fetching remote OS version",
        event_type="get_remote_os_version",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command="cat /etc/os-release",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="get_remote_ip_addresses",
    input_model=GetRemoteIPAddressesInput,
    tags=["ssh", "remote", "network", "ip", "midlevel"],
    description="Get the IP addresses of a remote machine.",
    safe_mode=True,
    purpose="Retrieve the IP addresses assigned to the remote machine",
    category="network",
)
def get_remote_ip_addresses(input_data: GetRemoteIPAddressesInput) -> str:
    """Return IP addresses assigned to the remote host.

:param input_data: SSH configuration.
:return: IP addresses string."""
    logger.info(
        "Fetching remote IP addresses",
        event_type="get_remote_ip_addresses",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command="hostname -I",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="check_logged_in_users",
    input_model=CheckLoggedInUsersInput,
    tags=["ssh", "remote", "users", "midlevel"],
    description="Check who is currently logged into a remote machine.",
    safe_mode=True,
    purpose="List users currently logged into the remote system",
    category="monitoring",
)
def check_logged_in_users(input_data: CheckLoggedInUsersInput) -> str:
    """Check who is currently logged into a remote system.

:param input_data: SSH credentials.
:return: List of logged in users."""
    logger.info(
        "Checking logged in users",
        event_type="check_logged_in_users",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host, command="who", ssh_key_path=input_data.ssh_key_path
        )
    )


@register_tool(
    name="get_last_login_times",
    input_model=GetLastLoginTimesInput,
    tags=["ssh", "remote", "users", "logins", "midlevel"],
    description="Get historical login data from the remote system using 'last'.",
    safe_mode=True,
    purpose="Display recent login history on the remote system",
    category="auth",
)
def get_last_login_times(input_data: GetLastLoginTimesInput) -> str:
    """Return recent login attempts on a remote system.

:param input_data: SSH parameters.
:return: Login history from 'last -a'."""
    logger.info(
        "Getting last login history",
        event_type="get_last_login_times",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command="last -a",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="get_remote_system_info",
    input_model=RemoteSysInfoInput,
    tags=["remote", "system", "wrapper"],
    description="Get basic system information from a remote host using uname -a.",
    safe_mode=True,
    purpose="Remotely retrieve system information like kernel, architecture, and hostname.",
    category="system",
)
def get_remote_system_info(input_data: RemoteSysInfoInput) -> str:
    """Use 'uname -a' to retrieve kernel and system info remotely.

:param input_data: Host and SSH key.
:return: System description."""
    logger.info(f"Retrieving remote system info from host {input_data.host}")
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command="uname -a",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="check_remote_processes",
    input_model=CheckRemoteProcessesInput,
    tags=["ssh", "remote", "process", "midlevel"],
    description="Retrieve the process list from a remote machine using 'ps aux'.",
    safe_mode=True,
    purpose="Retrieve a list of running processes on a remote machine",
    category="monitoring",
)
def check_remote_processes(input_data: CheckRemoteProcessesInput) -> str:
    """List running processes on a remote system using 'ps aux'.

:param input_data: SSH credentials.
:return: Raw process listing."""
    inner_input = RunRemoteCommandInput(
        host=input_data.host, command="ps aux", ssh_key_path=input_data.ssh_key_path
    )
    return run_remote_command(inner_input)


@register_tool(
    name="check_remote_memory_usage",
    input_model=CheckRemoteMemoryUsageInput,
    tags=["ssh", "remote", "memory", "usage", "midlevel"],
    description="Check memory usage on a remote machine using 'free -h'.",
    safe_mode=True,
    purpose="Get memory usage statistics from the remote machine",
    category="monitoring",
)
def check_remote_memory_usage(input_data: CheckRemoteMemoryUsageInput) -> str:
    """Use 'free -h' to check remote memory stats.

:param input_data: SSH credentials.
:return: Memory usage."""
    inner_input = RunRemoteCommandInput(
        host=input_data.host, command="free -h", ssh_key_path=input_data.ssh_key_path
    )
    return run_remote_command(inner_input)


@register_tool(
    name="check_remote_cpu_load",
    input_model=CheckRemoteCPULoadInput,
    tags=["ssh", "remote", "cpu", "load", "midlevel"],
    description="Get CPU load summary from a remote machine.",
    safe_mode=True,
    purpose="Check real-time CPU usage on a remote system",
    category="monitoring",
)
def check_remote_cpu_load(input_data: CheckRemoteCPULoadInput) -> str:
    """Fetch CPU load summary using 'top' command on remote host.

:param input_data: SSH credentials.
:return: CPU load details."""
    inner_input = RunRemoteCommandInput(
        host=input_data.host,
        command="top -bn1 | head -n 15",
        ssh_key_path=input_data.ssh_key_path,
    )
    return run_remote_command(inner_input)


@register_tool(
    name="check_remote_service_status",
    input_model=CheckRemoteServiceStatusInput,
    tags=["ssh", "service", "status", "midlevel"],
    description="Check status of a systemd service on a remote machine.",
    safe_mode=True,
    purpose="Check systemd service status remotely",
    category="system",
)
def check_remote_service_status(input_data: CheckRemoteServiceStatusInput) -> str:
    """Check systemd service status remotely.

:param input_data: Service name and SSH info.
:return: Status of the specified service."""
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command=f"systemctl status {input_data.service_name}",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="run_remote_benchmark",
    input_model=RunRemoteBenchmarkInput,
    tags=["benchmark", "timeout", "midlevel"],
    description="Run a benchmark or test command locally with timeout enforcement.",
    safe_mode=True,
    purpose="Run a timed benchmark command on the local system",
    category="diagnostic",
)
def run_remote_benchmark(input_data: RunRemoteBenchmarkInput) -> str:
    """Execute a timed command on a remote system.

:param input_data: Command and SSH configuration.
:return: Command output or timeout error."""
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command=input_data.command,
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="create_remote_user",
    input_model=CreateRemoteUserInput,
    tags=["ssh", "user", "create", "midlevel"],
    description="Create a user on the remote system with home directory.",
    safe_mode=True,
    purpose="Create a new user account on a remote machine",
    category="auth",
)
def create_remote_user(input_data: CreateRemoteUserInput) -> str:
    """Create a user account on a remote machine.

:param input_data: Hostname, username, SSH credentials.
:return: Command result."""
    logger.info(
        "Creating user on remote host",
        event_type="create_remote_user",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command=f"sudo useradd -m {input_data.username}",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="lock_remote_user_account",
    category="auth",
    input_model=LockRemoteUserAccountInput,
    tags=["ssh", "user", "lock", "midlevel"],
    description="Lock a user account on the remote host (passwd -l).",
    safe_mode=True,
    purpose="Lock a user account on a remote host",
)
def lock_remote_user_account(input_data: LockRemoteUserAccountInput) -> str:
    """Lock an existing user account remotely.

:param input_data: Host and username to lock.
:return: Lock confirmation."""
    logger.info(
        "Locking user account",
        event_type="lock_remote_user_account",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command=f"sudo passwd -l {input_data.username}",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="add_user_to_group",
    input_model=AddUserToGroupInput,
    tags=["ssh", "user", "group", "midlevel"],
    description="Add a user to a group on the remote system.",
    safe_mode=True,
    purpose="Add a user to a group on the remote machine",
    category="auth",
)
def add_user_to_group(input_data: AddUserToGroupInput) -> str:
    """Add a user to a group on a remote system.

:param input_data: Group name, user, and SSH credentials.
:return: Command result."""
    logger.info(
        "Adding user to group",
        event_type="add_user_to_group",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command=f"sudo usermod -aG {input_data.group} {input_data.username}",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="reset_remote_password",
    input_model=ResetRemotePasswordInput,
    tags=["ssh", "interactive", "user", "midlevel"],
    description="Reset the password for a user on a remote host.",
    safe_mode=True,
    purpose="Reset a user's password interactively on a remote host",
    category="auth",
)
def reset_remote_password(input_data: ResetRemotePasswordInput) -> str:
    """Reset a remote user’s password interactively.

:param input_data: User account and SSH settings.
:return: Command result or failure string."""
    logger.info(
        "Resetting password remotely",
        event_type="reset_remote_password",
        data=input_data.dict(),
    )
    return run_remote_interactive_command(
        RunRemoteInteractiveCommandInput(
            host=input_data.host,
            command=f"sudo passwd {input_data.username}",
            user=input_data.user(),
        )
    )
