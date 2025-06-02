"""
Shell wrapper tools for executing and capturing command-line operations.

Enables dynamic interaction with shell environments, script execution, and sanitized I/O capture.
"""

import subprocess
from typing import Optional

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.tools.primitives import (
    run_local_command,
    RunLocalCommandInput,
    check_remote_file_exists,
    CheckRemoteFileExistsInput,
    run_remote_script,
    RunRemoteScriptInput,
)
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class RunScriptIfAbsentInput(BaseModel):
    """
    Represents the RunScriptIfAbsentInput class.

    Describes the input required to run a script on a remote machine only if it doesn't already exist.
    """

    host: str = Field(description="Remote host (user@host).")
    check_path: str = Field(description="Remote file to check existence for.")
    local_script_path: str = Field(
        description="Path to the script to upload and execute."
    )
    remote_script_path: str = Field(
        description="Path to place script on remote system."
    )
    ssh_key_path: str = Field(description="SSH key for authentication.")


class SafeShellInput(BaseModel):
    """
    Represents the SafeShellInput class.

    Wraps shell command input for tools that perform safety checks or sanitization.
    """

    command: str = Field(description="Shell command to execute locally.")


class RunRemoteCommandInput(BaseModel):
    """
    Represents the RunRemoteCommandInput class.

    Contains parameters for executing a single command on a remote system via SSH.
    """

    host: str = Field(description="Remote host (user@host).")
    command: str = Field(description="The command to run.")
    extra_args: str = Field(
        default="", description="Optional arguments to pass to the command."
    )
    ssh_key_path: str = Field(description="Path to SSH private key.")


class SimpleShellCommandInput(BaseModel):
    """
    Represents the SimpleShellCommandInput class.

    Defines a basic shell command with optional environment and working directory overrides.
    """

    command: str = Field(description="Name of the command to run.")
    extra_args: Optional[str] = Field(
        default="", description="Extra arguments to pass to the command."
    )


class RunRemoteBackgroundCommandInput(BaseModel):
    """
    Represents the RunRemoteBackgroundCommandInput class.

    Describes a remote command to be launched in the background using nohup or similar tools.
    """

    host: str = Field(description="Remote host to connect to")
    user: str = Field(description="SSH username")
    command: str = Field(description="Shell command to run in the background")
    ssh_key_path: str = Field(description="SSH private key")


class RunRemoteInteractiveCommandInput(BaseModel):
    """
    RunRemoteInteractiveCommandInput class.
    """

    host: str = Field(description="Remote host to connect to")
    user: str = Field(description="SSH username")
    command: str = Field(description="Interactive shell command to run")


class RunRemotePythonSnippetInput(BaseModel):
    """
    RunRemotePythonSnippetInput class.
    """

    host: str = Field(description="Remote host to connect to")
    user: str = Field(description="SSH username")
    code: str = Field(description="Python code to run remotely using 'python3 -c'")


@register_tool(
    name="run_remote_command",
    input_model=RunRemoteCommandInput,
    tags=["system", "remote", "ssh"],
    description="Execute a shell command on a remote host via SSH and return output.",
    safe_mode=True,
    purpose="Allow remote shell execution using SSH.",
    category="system",
)
def run_remote_command(input_data: RunRemoteCommandInput) -> str:
    """
    run_remote_command.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    ssh_target = f"{input_data.host}"
    try:
        result = subprocess.run(
            ["ssh", ssh_target, input_data.command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[shell tool] [ERROR] Failed to run remote command: {str(e)}")
        return f"[ERROR] Failed to run remote command: {str(e)}"


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
    """
    run_remote_background_command.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    ssh_target = f"{input_data.user}@{input_data.host}"
    wrapped_command = f"nohup {input_data.command} > /dev/null 2>&1 &"
    try:
        result = subprocess.run(
            ["ssh", ssh_target, wrapped_command],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[shell tool] [ERROR] Failed to run remote background command: {str(e)}")
        return f"[ERROR] Failed to run remote background command: {str(e)}"


@register_tool(
    name="run_remote_interactive_command",
    input_model=RunRemoteInteractiveCommandInput,
    tags=["system", "remote", "ssh", "interactive"],
    description="Execute an interactive command on a remote host (e.g. tools requiring stdin).",
    safe_mode=False,
    purpose="Support remote tools that require user interaction or complex input/output streams.",
    category="system",
)
def run_remote_interactive_command(input_data: RunRemoteInteractiveCommandInput) -> str:
    """
    run_remote_interactive_command.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    ssh_target = f"{input_data.user}@{input_data.host}"
    try:
        result = subprocess.run(
            ["ssh", "-tt", ssh_target, input_data.command],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[shell tool] [ERROR] Failed to run remote interactive command: {str(e)}")
        return f"[ERROR] Failed to run remote interactive command: {str(e)}"


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
    """
    run_remote_python_snippet.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    ssh_target = f"{input_data.user}@{input_data.host}"
    escaped_code = input_data.code.replace('"', '\\"')
    remote_command = f'python3 -c "{escaped_code}"'
    try:
        result = subprocess.run(
            ["ssh", ssh_target, remote_command],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[shell tool] [ERROR] Failed to run remote Python snippet: {str(e)}")
        return f"[ERROR] Failed to run remote Python snippet: {str(e)}"


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
    """
    run_script_if_absent.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("Conditionally running remote script")
    exists = check_remote_file_exists(
        CheckRemoteFileExistsInput(
            file_path=input_data.check_path,
            host=input_data.host,
            ssh_key_path=input_data.ssh_key_path,
        )
    )
    if "Exists" in exists:
        return f"[INFO] File {input_data.check_path} already exists. Skipping script."
    return run_remote_script(
        RunRemoteScriptInput(
            script_path=input_data.local_script_path,
            remote_path=input_data.remote_script_path,
            host=input_data.host,
            ssh_key_path=input_data.ssh_key_path,
        )
    )


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
    """
    safe_shell_execute.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    dangerous = ["rm ", "shutdown", "halt", "reboot", ":(){", "mkfs", "dd ", ">:"]
    lowered = input_data.command.lower()
    if any((term in lowered for term in dangerous)):
        return "[BLOCKED] Command contains dangerous operations."
    logger.info(f"Executing safe local shell command: {input_data.command}")
    return run_local_command(RunLocalCommandInput(command=input_data.command))
