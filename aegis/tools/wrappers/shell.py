# aegis/tools/wrappers/shell.py
"""
Shell wrapper tools for executing local and remote commands.

This module provides tools for more complex shell interactions, such as
running commands in the background or conditionally executing scripts based
on the state of the remote system.
"""

import shlex

from pydantic import BaseModel, Field

from aegis.executors.ssh_exec import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import MachineTargetInput
from aegis.utils.logger import setup_logger
from aegis.utils.machine_loader import get_machine

logger = setup_logger(__name__)


class RunScriptIfAbsentInput(MachineTargetInput):
    """Input model for conditionally running a remote script.

    :ivar check_path: Remote file to check existence for.
    :vartype check_path: str
    :ivar local_script_path: Path to the script to upload and execute.
    :vartype local_script_path: str
    :ivar remote_script_path: Path to place script on remote system.
    :vartype remote_script_path: str
    """

    check_path: str = Field(description="Remote file to check existence for.")
    local_script_path: str = Field(
        description="Path to the script to upload and execute."
    )
    remote_script_path: str = Field(
        description="Path to place script on remote system."
    )


class RunRemoteBackgroundCommandInput(MachineTargetInput):
    """Input model for running a command in the background on a remote host.

    :ivar command: Shell command to run in the background.
    :vartype command: str
    """

    command: str = Field(description="Shell command to run in the background.")


class RunRemotePythonSnippetInput(MachineTargetInput):
    """Input model for running a Python snippet on a remote host.

    :ivar code: Python code to run remotely using 'python3 -c'.
    :vartype code: str
    """

    code: str = Field(description="Python code to run remotely using 'python3 -c'.")


@register_tool(
    name="run_remote_background_command",
    input_model=RunRemoteBackgroundCommandInput,
    tags=["system", "remote", "ssh", "background", "wrapper"],
    description="Run a background command remotely using nohup.",
    safe_mode=True,
    purpose="Launch persistent background processes on remote machines.",
    category="system",
)
def run_remote_background_command(input_data: RunRemoteBackgroundCommandInput) -> str:
    """Runs a command in the background on a remote host using nohup.

    :param input_data: An object containing machine name and the command.
    :type input_data: RunRemoteBackgroundCommandInput
    :return: The output from the SSH command (usually empty for nohup success).
    :rtype: str
    """
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    # The `&` ensures it runs in the background. nohup prevents it from being killed on session exit.
    wrapped_command = f"nohup {input_data.command} > /dev/null 2>&1 &"
    # executor.run() returns output on success or raises ToolExecutionError
    # For nohup like this, stdout/stderr are redirected, so output is usually empty.
    # We'll return a confirmation message.
    executor.run(wrapped_command)
    return f"Successfully launched background command on {input_data.machine_name}: {input_data.command}"


@register_tool(
    name="run_remote_python_snippet",
    input_model=RunRemotePythonSnippetInput,
    tags=["system", "remote", "ssh", "python", "wrapper"],
    description="Run a short Python snippet remotely using 'python3 -c'.",
    safe_mode=False,
    purpose="Quick remote introspection or scripting using Python.",
    category="system",
)
def run_remote_python_snippet(input_data: RunRemotePythonSnippetInput) -> str:
    """Executes a Python code snippet on a remote host.

    :param input_data: An object containing the machine name and Python code.
    :type input_data: RunRemotePythonSnippetInput
    :return: The output from the remote Python execution.
    :rtype: str
    """
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    remote_command = f"python3 -c {shlex.quote(input_data.code)}"
    return executor.run(remote_command)


@register_tool(
    name="run_script_if_absent",
    input_model=RunScriptIfAbsentInput,
    tags=["ssh", "conditional", "script", "wrapper"],
    description="Upload and run a script only if a given file is absent.",
    safe_mode=True,
    purpose="Conditionally execute a script if a given file is missing",
    category="system",
)
def run_script_if_absent(input_data: RunScriptIfAbsentInput) -> str:
    """Checks for a file's existence and runs a script if it's missing.

    This tool is useful for idempotent setup operations, ensuring that an
    installation or configuration script is only run once.

    :param input_data: An object containing paths for checking, uploading, and execution.
    :type input_data: RunScriptIfAbsentInput
    :return: An informational message or the output of the script execution.
    :rtype: str
    """
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)

    if executor.check_file_exists(input_data.check_path):
        return f"[INFO] File {input_data.check_path} already exists. Skipping script."

    # executor.upload will raise ToolExecutionError if it fails.
    # It returns a success message string if successful.
    upload_message = executor.upload(
        input_data.local_script_path, input_data.remote_script_path
    )
    logger.info(upload_message)  # Log the success message from upload

    # If upload was successful, run the script. executor.run will raise if script fails.
    script_output = executor.run(f"bash {shlex.quote(input_data.remote_script_path)}")
    return script_output
