"""
Integration wrappers for connecting internal agent functionality with external systems.

These tools act as bridges to services such as APIs, dashboards, or remote logging systems.
"""

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.tools.wrappers.shell import (
    run_remote_command,
    run_remote_background_command,
    RunRemoteCommandInput,
    RunRemoteBackgroundCommandInput
)
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class ScheduleCronJobInput(BaseModel):
    """
    ScheduleCronJobInput class.
    """

    host: str = Field(description="Remote host (user@host).")
    cron_entry: str = Field(description="The crontab line to schedule.")
    ssh_key_path: str = Field(description="SSH key for authentication.")


class RunDiagnosticsBundleInput(BaseModel):
    """
    RunDiagnosticsBundleInput class.
    """

    host: str = Field(description="Remote host (user@host).")
    ssh_key_path: str = Field(description="SSH key for authentication.")


class SpawnBackgroundMonitorInput(BaseModel):
    """
    SpawnBackgroundMonitorInput class.
    """

    host: str = Field(description="Remote host (user@host).")
    command: str = Field(description="Command to run in background.")
    ssh_key_path: str = Field(description="SSH key for authentication.")


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
    """
    schedule_cron_job.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Scheduling cron job", event_type="schedule_cron_job", data=input_data.dict()
    )
    cron_cmd = f'(crontab -l 2>/dev/null; echo "{input_data.cron_entry}") | crontab -'
    return run_remote_command(
        RunRemoteCommandInput(
            command=cron_cmd, host=input_data.host, ssh_key_path=input_data.ssh_key_path
        )
    )


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
    """
    run_diagnostics_bundle.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    bundle = " && ".join(["uptime", "free -h", "df -h", "ps aux", "who", "ss -tuln"])
    logger.info(
        "Running diagnostics bundle",
        event_type="run_diagnostics_bundle",
        data=input_data.dict,
    )
    return run_remote_command(
        RunRemoteCommandInput(
            command=bundle, host=input_data.host, ssh_key_path=input_data.ssh_key_path
        )
    )


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
    """
    spawn_background_monitor.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Spawning background monitor",
        event_type="spawn_background_monitor",
        data=input_data.dict(),
    )
    return run_remote_background_command(
        RunRemoteBackgroundCommandInput(
            command=input_data.command,
            user=input_data.user,
            host=input_data.host,
            ssh_key_path=input_data.ssh_key_path,
        )
    )
