# aegis/tools/wrappers/integration.py
"""
Integration wrappers for connecting AEGIS to external systems or performing
complex, multi-step remote actions.

These tools often combine multiple primitives or executors to achieve a
higher-level goal, like scheduling a cron job or running a diagnostic bundle.
"""

import shlex
from typing import Tuple

from pydantic import BaseModel, Field

from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def _get_user_host(host_str: str) -> Tuple[str, str]:
    """Helper to split 'user@host' strings.

    :param host_str: The input string, e.g., "user@example.com".
    :type host_str: str
    :raises ValueError: If the string is not in the expected format.
    :return: A tuple containing the user and host.
    :rtype: Tuple[str, str]
    """
    if "@" not in host_str:
        raise ValueError(f"Host string '{host_str}' must be in 'user@host' format for this tool.")
    user, host = host_str.split("@", 1)
    return user, host


class ScheduleCronJobInput(BaseModel):
    """Input model for scheduling a cron job on a remote host."""
    host: str = Field(description="Remote host (e.g., 'user@host.com').")
    cron_entry: str = Field(description="The crontab line to schedule.")
    ssh_key_path: str | None = Field(None, description="SSH key for authentication.")


class RunDiagnosticsBundleInput(BaseModel):
    """Input model for running a diagnostic bundle on a remote host."""
    host: str = Field(description="Remote host (e.g., 'user@host.com').")
    ssh_key_path: str | None = Field(None, description="SSH key for authentication.")


class SpawnBackgroundMonitorInput(BaseModel):
    """Input model for spawning a background process on a remote host."""
    host: str = Field(description="Remote host (e.g., 'user@host.com').")
    command: str = Field(description="Command to run in background.")
    ssh_key_path: str | None = Field(None, description="SSH key for authentication.")


@register_tool(
    name="schedule_cron_job",
    input_model=ScheduleCronJobInput,
    tags=["ssh", "cron", "midlevel"],
    description="Add a cron job to a remote user's crontab.",
    safe_mode=True,
    purpose="Add a cron job to the remote user's crontab",
    category="system",
)
def schedule_cron_job(input_data: ScheduleCronJobInput) -> str:
    """Adds a cron job on a remote system.

    :param input_data: An object containing host info and the cron entry.
    :type input_data: ScheduleCronJobInput
    :return: The result of the crontab command.
    :rtype: str
    """
    user, host = _get_user_host(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    cron_cmd = f'(crontab -l 2>/dev/null; echo {shlex.quote(input_data.cron_entry)}) | crontab -'
    return executor.run(cron_cmd)


@register_tool(
    name="run_diagnostics_bundle",
    input_model=RunDiagnosticsBundleInput,
    tags=["ssh", "diagnostics", "bundle", "midlevel"],
    description="Run a bundle of common diagnostic commands on a remote system.",
    safe_mode=True,
    purpose="Run a set of system diagnostics on the remote machine",
    category="diagnostic",
)
def run_diagnostics_bundle(input_data: RunDiagnosticsBundleInput) -> str:
    """Runs a series of diagnostic commands on a remote host.

    :param input_data: An object containing host connection details.
    :type input_data: RunDiagnosticsBundleInput
    :return: The combined output of all diagnostic commands.
    :rtype: str
    """
    user, host = _get_user_host(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    bundle = "uptime && echo '---' && free -h && echo '---' && df -h && echo '---' && ps aux | head -n 10 && echo '---' && who && echo '---' && ss -tuln"
    return executor.run(bundle)


@register_tool(
    name="spawn_background_monitor",
    input_model=SpawnBackgroundMonitorInput,
    tags=["ssh", "background", "monitor", "midlevel"],
    description="Run a background process on a remote host using nohup.",
    safe_mode=True,
    purpose="Run a persistent background command via nohup",
    category="system",
)
def spawn_background_monitor(input_data: SpawnBackgroundMonitorInput) -> str:
    """Runs a command in the background on a remote host using nohup.

    :param input_data: An object containing host info and the command to run.
    :type input_data: SpawnBackgroundMonitorInput
    :return: The output from launching the background process.
    :rtype: str
    """
    user, host = _get_user_host(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    wrapped_command = f"nohup {input_data.command} > /dev/null 2>&1 &"
    return executor.run(wrapped_command)
