# aegis/tools/wrappers/shell.py
"""
Shell wrapper tools for executing local and remote commands.

This module provides tools for more complex shell interactions, such as
running commands in the background or conditionally executing scripts based
on the state of the remote system.
"""

import shlex
from typing import Tuple, Optional

from pydantic import BaseModel, Field

from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.tools.primitives.primitive_system import (
    run_local_command,
    RunLocalCommandInput,
)
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
        raise ValueError(
            f"Host string '{host_str}' must be in 'user@host' format for this tool."
        )
    user, host = host_str.split("@", 1)
    return user, host


class RunScriptIfAbsentInput(BaseModel):
    """Input model for conditionally running a remote script."""

    host: str = Field(description="Remote host (e.g., 'user@host.com').")
    check_path: str = Field(description="Remote file to check existence for.")
    local_script_path: str = Field(
        description="Path to the script to upload and execute."
    )
    remote_script_path: str = Field(
        description="Path to place script on remote system."
    )
    ssh_key_path: str | None = Field(None, description="SSH key for authentication.")


class SafeShellInput(BaseModel):
    """Input model for the safe local shell execution tool."""

    command: str = Field(description="Shell command to execute locally.")


class RunRemoteBackgroundCommandInput(BaseModel):
    """Input model for running a command in the background on a remote host."""

    host: str = Field(description="Remote host to connect to (e.g., 'user@host.com').")
    command: str = Field(description="Shell command to run in the background.")
    ssh_key_path: str | None = Field(None, description="SSH private key.")


class RunRemotePythonSnippetInput(BaseModel):
    """Input model for running a Python snippet on a remote host."""

    host: str = Field(description="Remote host to connect to (e.g., 'user@host.com').")
    code: str = Field(description="Python code to run remotely using 'python3 -c'.")
    ssh_key_path: str | None = Field(
        None, description="Optional path to SSH private key."
    )


@register_tool(
    name="run_remote_background_command",
    input_model=RunRemoteBackgroundCommandInput,
    tags=["system", "remote", "ssh", "background"],
    description="Run a background command remotely using nohup.",
    safe_mode=True,
    purpose="Launch persistent background processes on remote machines.",
    category="system",
)
def run_remote_background_command(input_data: RunRemoteBackgroundCommandInput) -> str:
    """Runs a command in the background on a remote host using nohup.

    :param input_data: An object containing the host and command to run.
    :type input_data: RunRemoteBackgroundCommandInput
    :return: The output from launching the background process.
    :rtype: str
    """
    user, host = _get_user_host(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    # The `&` ensures it runs in the background. nohup prevents it from being killed on session exit.
    wrapped_command = f"nohup {input_data.command} > /dev/null 2>&1 &"
    return executor.run(wrapped_command)


@register_tool(
    name="run_remote_python_snippet",
    input_model=RunRemotePythonSnippetInput,
    tags=["system", "remote", "ssh", "python"],
    description="Run a short Python snippet remotely using 'python3 -c'.",
    safe_mode=False,
    purpose="Quick remote introspection or scripting using Python.",
    category="system",
)
def run_remote_python_snippet(input_data: RunRemotePythonSnippetInput) -> str:
    """Executes a Python code snippet on a remote host.

    :param input_data: An object containing the host and Python code.
    :type input_data: RunRemotePythonSnippetInput
    :return: The output of the executed Python snippet.
    :rtype: str
    """
    user, host = _get_user_host(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    remote_command = f"python3 -c {shlex.quote(input_data.code)}"
    return executor.run(remote_command)


@register_tool(
    name="run_script_if_absent",
    input_model=RunScriptIfAbsentInput,
    tags=["ssh", "conditional", "script", "midlevel"],
    description="Upload and run a script only if a given file is absent.",
    safe_mode=True,
    purpose="Conditionally execute a script if a given file is missing",
    category="system",
)
def run_script_if_absent(input_data: RunScriptIfAbsentInput) -> str:
    """Checks for a file's existence and runs a script if it's missing.

    :param input_data: An object containing paths and host info.
    :type input_data: RunScriptIfAbsentInput
    :return: A status message or the output of the script.
    :rtype: str
    """
    user, host = _get_user_host(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)

    if executor.check_file_exists(input_data.check_path):
        return f"[INFO] File {input_data.check_path} already exists. Skipping script."

    upload_result = executor.upload(
        input_data.local_script_path, input_data.remote_script_path
    )
    if "[ERROR]" in upload_result:
        return f"[ERROR] Script upload failed: {upload_result}"

    return executor.run(f"bash {shlex.quote(input_data.remote_script_path)}")


@register_tool(
    name="safe_shell_execute",
    input_model=SafeShellInput,
    tags=["shell", "wrapper", "local", "safe"],
    description="Run a local shell command after validating it for safety.",
    safe_mode=True,
    purpose="Safely run local shell commands with basic validation.",
    category="system",
)
def safe_shell_execute(input_data: SafeShellInput) -> str:
    """A wrapper to run local commands with a basic safety check.

    :param input_data: An object containing the command to run.
    :type input_data: SafeShellInput
    :return: The output of the command or a blocking message.
    :rtype: str
    """
    dangerous = ["rm -rf", "shutdown", "halt", "reboot", ":(){", "mkfs", "dd "]
    lowered = input_data.command.lower()
    if any(term in lowered for term in dangerous):
        return "[BLOCKED] Command contains potentially dangerous operations."
    logger.info(f"Executing safe local shell command: {input_data.command}")
    return run_local_command(
        RunLocalCommandInput(command=input_data.command, shell=True)
    )
