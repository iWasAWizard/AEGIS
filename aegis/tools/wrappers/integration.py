# aegis/tools/wrappers/integration.py
"""
Integration wrappers for connecting AEGIS to external systems or performing
complex, multi-step remote actions.

These tools often combine multiple primitives or executors to achieve a
higher-level goal, like scheduling a cron job or running a diagnostic bundle.
"""

import shlex

from pydantic import Field

from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import MachineTargetInput
from aegis.utils.logger import setup_logger
from aegis.utils.machine_loader import get_machine

logger = setup_logger(__name__)


class ScheduleCronJobInput(MachineTargetInput):
    """Input model for scheduling a cron job on a remote host.

    :ivar cron_entry: The full crontab line to schedule (e.g., "*/5 * * * * /path/to/script.sh").
    :vartype cron_entry: str
    """

    cron_entry: str = Field(description="The crontab line to schedule.")


class RunDiagnosticsBundleInput(MachineTargetInput):
    """Input model for running a diagnostic bundle on a remote host. Takes no arguments."""

    pass


class SpawnBackgroundMonitorInput(MachineTargetInput):
    """Input model for spawning a background process on a remote host.

    :ivar command: Command to run in background.
    :vartype command: str
    """

    command: str = Field(description="Command to run in background.")


@register_tool(
    name="schedule_cron_job",
    input_model=ScheduleCronJobInput,
    tags=["ssh", "cron", "midlevel", "wrapper"],
    description="Add a cron job to a remote user's crontab.",
    safe_mode=True,
    purpose="Add a cron job to the remote user's crontab",
    category="system",
)
def schedule_cron_job(input_data: ScheduleCronJobInput) -> str:
    """Adds a cron job on a remote system.

    This tool constructs a command that safely appends a new entry to the
    current user's crontab without overwriting existing jobs.

    :param input_data: An object containing the machine name and crontab entry.
    :type input_data: ScheduleCronJobInput
    :return: The output of the crontab command (usually empty on success) or a success message.
    :rtype: str
    """
    logger.info(f"Scheduling cron job on machine: {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    cron_cmd = f"(crontab -l 2>/dev/null; echo {shlex.quote(input_data.cron_entry)}) | crontab -"
    # executor.run() raises on error. crontab command is usually silent on success.
    executor.run(cron_cmd)
    return f"Successfully scheduled cron job on {input_data.machine_name}: '{input_data.cron_entry}'"


@register_tool(
    name="run_diagnostics_bundle",
    input_model=RunDiagnosticsBundleInput,
    tags=["ssh", "diagnostics", "bundle", "midlevel", "wrapper"],
    description="Run a bundle of common diagnostic commands on a remote system.",
    safe_mode=True,
    purpose="Run a set of system diagnostics on the remote machine",
    category="diagnostic",
)
def run_diagnostics_bundle(input_data: RunDiagnosticsBundleInput) -> str:
    """Runs a series of diagnostic commands on a remote host.

    This tool executes a predefined "bundle" of common diagnostic commands
    (uptime, free, df, ps, who, ss) in a single SSH session, providing a
    quick snapshot of the remote system's health.

    :param input_data: An object containing the target machine name.
    :type input_data: RunDiagnosticsBundleInput
    :return: The combined output of all diagnostic commands.
    :rtype: str
    """
    logger.info(f"Running diagnostics bundle on machine: {input_data.machine_name}")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    bundle = (
        "uptime && echo '---' && free -h && echo '---' && df -h && "
        "echo '---' && ps aux | head -n 10 && echo '---' && who && echo '---' && ss -tuln"
    )
    return executor.run(bundle)


@register_tool(
    name="spawn_background_monitor",
    input_model=SpawnBackgroundMonitorInput,
    tags=["ssh", "background", "monitor", "midlevel", "wrapper"],
    description="Run a background process on a remote host using nohup.",
    safe_mode=True,
    purpose="Run a persistent background command via nohup",
    category="system",
)
def spawn_background_monitor(input_data: SpawnBackgroundMonitorInput) -> str:
    """Runs a command in the background on a remote host using nohup.

    This ensures the command will continue running even after the SSH
    session is closed. Output is redirected to /dev/null.

    :param input_data: An object containing the machine name and the command to run.
    :type input_data: SpawnBackgroundMonitorInput
    :return: The output of the nohup command (typically empty on success) or a success message.
    :rtype: str
    """
    logger.info(
        f"Spawning background monitor on {input_data.machine_name} with command: '{input_data.command}'"
    )
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    wrapped_command = f"nohup {input_data.command} > /dev/null 2>&1 &"
    # executor.run() raises on error. nohup command is silent on success.
    executor.run(wrapped_command)
    return f"Successfully spawned background monitor on {input_data.machine_name} with command: '{input_data.command}'"
