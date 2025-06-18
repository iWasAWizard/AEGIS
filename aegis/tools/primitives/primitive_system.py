# aegis/tools/primitives/primitive_system.py
"""
Primitive tools for local system interaction and diagnostics.

This module provides fundamental tools for interacting with the local operating
system, including running shell commands, killing processes, and gathering
basic hardware and system statistics.
"""

import subprocess

import psutil
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class KillProcessInput(BaseModel):
    """Input for killing a process by its Process ID (PID).

    :ivar pid: The Process ID (PID) of the process to kill.
    :vartype pid: int
    """

    pid: int = Field(..., description="The Process ID (PID) of the process to kill.")


class GetLocalMemoryInfoInput(BaseModel):
    """Input for getting local memory information. Takes no arguments."""

    pass


class RunLocalCommandInput(BaseModel):
    """Input for running a command on the local shell.

    :ivar command: The shell command to execute locally.
    :vartype command: str
    :ivar shell: Whether to use the shell for execution. Recommended to be True for complex commands.
    :vartype shell: bool
    """

    command: str = Field(..., description="The shell command to execute locally.")
    shell: bool = Field(
        default=True,
        description="Whether to use the shell for execution. Recommended to be True for complex commands.",
    )


class GetRandomBytesInput(BaseModel):
    """Input for getting random bytes from the OS source.

    :ivar length: Number of bytes to read from /dev/random.
    :vartype length: int
    """

    length: int = Field(
        default=32, gt=0, description="Number of bytes to read from /dev/random."
    )


# === Tools ===


@register_tool(
    name="kill_local_process",
    input_model=KillProcessInput,
    description="Terminates a local process by its PID using a SIGKILL signal.",
    tags=["system", "process", "primitive"],
    safe_mode=False,
    purpose="Forcibly terminate a running process on the local machine.",
    category="system",
)
def kill_local_process(input_data: KillProcessInput) -> str:
    """Executes `kill -9` on the given PID.

    :param input_data: An object containing the PID of the process to kill.
    :type input_data: KillProcessInput
    :return: A string indicating the success or failure of the operation.
    :rtype: str
    """
    pid_to_kill = str(input_data.pid)
    logger.info(f"Attempting to kill local PID: {pid_to_kill}")
    try:
        result = subprocess.run(["kill", "-9", pid_to_kill], capture_output=True, text=True, timeout=5, check=False)
        if result.returncode == 0:
            logger.info(f"Successfully sent SIGKILL to PID {pid_to_kill}")
            return f"Successfully killed process {pid_to_kill}"
        else:
            error_message = (result.stderr or result.stdout).strip()
            logger.error(f"Failed to kill PID {pid_to_kill}: {error_message}")
            return f"[ERROR] Kill command failed: {error_message}"
    except Exception as e:
        logger.exception(f"An exception occurred while trying to kill PID {pid_to_kill}")
        raise ToolExecutionError(f"Exception occurred while killing process: {e}") from e


@register_tool(
    name="run_local_command",
    input_model=RunLocalCommandInput,
    description="Runs a shell command on the local machine and returns its output.",
    tags=["system", "shell", "primitive"],
    safe_mode=False,
    purpose="Execute a shell command on the local machine.",
    category="system",
)
def run_local_command(input_data: RunLocalCommandInput) -> str:
    """Executes a given shell command locally using the subprocess module.

    :param input_data: An object containing the command string to execute.
    :type input_data: RunLocalCommandInput
    :return: The combined stdout and stderr from the executed command.
    :rtype: str
    """
    logger.info(f"Executing local command: {input_data.command}")
    try:
        result = subprocess.run(input_data.command, shell=input_data.shell, capture_output=True, text=True, timeout=60,
                                check=False)
        output = result.stdout.strip()
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr.strip()}"
        return output
    except Exception as e:
        logger.exception(f"Exception during local command execution: {input_data.command}")
        raise ToolExecutionError(f"Command execution failed: {e}") from e


def _format_bytes_to_gb(num_bytes: int) -> str:
    """Helper function to format bytes into a human-readable GB string."""
    return f"{num_bytes / (1024 ** 3):.2f} GB"


@register_tool(
    name="get_local_memory_info",
    input_model=GetLocalMemoryInfoInput,
    description="Returns local system memory usage statistics using psutil.",
    tags=["system", "memory", "monitoring", "primitive"],
    safe_mode=True,
    purpose="Retrieve detailed memory statistics from the local machine.",
    category="system",
)
def get_local_memory_info(_: GetLocalMemoryInfoInput) -> str:
    """Uses the psutil library to return detailed memory statistics.

    :param _: This tool takes no arguments.
    :type _: GetLocalMemoryInfoInput
    :return: A formatted string of memory statistics.
    :rtype: str
    :raises ToolExecutionError: If `psutil` is not installed or fails.
    """
    try:
        logger.info("Retrieving local memory info via psutil.")
        mem = psutil.virtual_memory()
        result = f"Total: {_format_bytes_to_gb(mem.total)}\n" \
                 f"Available: {_format_bytes_to_gb(mem.available)}\n" \
                 f"Used: {_format_bytes_to_gb(mem.used)} (Percent: {mem.percent}%)"
        return result
    except Exception as e:
        logger.warning(f"psutil failed to get memory info: {e}. Is psutil installed?")
        raise ToolExecutionError(f"Could not retrieve memory info. psutil might be missing or failed: {e}") from e


@register_tool(
    name="get_random_bytes_as_hex",
    input_model=GetRandomBytesInput,
    description="Returns a hex-encoded string of random bytes from the OS.",
    tags=["system", "random", "primitive"],
    safe_mode=True,
    purpose="Generate a cryptographically secure random string.",
    category="system",
)
def get_random_bytes_as_hex(input_data: GetRandomBytesInput) -> str:
    """Reads raw bytes from the OS's entropy source and hex-encodes them.

    This tool typically uses `/dev/random` on Linux/macOS, providing a source
    of cryptographically secure random data.

    :param input_data: An object specifying the number of bytes to read.
    :type input_data: GetRandomBytesInput
    :return: A hex-encoded string of random data.
    :rtype: str
    :raises ToolExecutionError: If the OS entropy source cannot be read.
    """
    logger.info(f"Reading {input_data.length} bytes from /dev/random.")
    try:
        with open("/dev/random", "rb") as f:
            return f.read(input_data.length).hex()
    except Exception as e:
        logger.exception("Failed to read from /dev/random")
        raise ToolExecutionError(f"Could not read random bytes: {e}") from e
