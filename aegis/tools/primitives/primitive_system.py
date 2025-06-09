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

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===

class KillProcessInput(BaseModel):
    """Input for killing a process by its Process ID (PID)."""
    pid: int = Field(..., description="The Process ID (PID) of the process to kill.")


class GetLocalMemoryInfoInput(BaseModel):
    """Input for getting local memory information. Takes no arguments."""
    pass


class RunLocalCommandInput(BaseModel):
    """Input for running a command on the local shell."""
    command: str = Field(..., description="The shell command to execute locally.")
    shell: bool = Field(
        default=True,
        description="Whether to use the shell for execution. Recommended to be True for complex commands.",
    )


class GetRandomBytesInput(BaseModel):
    """Input for getting random bytes from the OS source."""
    length: int = Field(default=32, gt=0, description="Number of bytes to read from /dev/random.")


# === Tools ===

@register_tool(
    name="kill_local_process",
    input_model=KillProcessInput,
    description="Terminates a local process by its PID using a SIGKILL signal.",
    tags=["system", "process", "primitive"],
    safe_mode=False,  # This is a dangerous operation.
    purpose="Forcibly terminate a running process on the local machine.",
    category="system",
)
def kill_local_process(input_data: KillProcessInput) -> str:
    """Executes `kill -9` on the given PID on Unix-based systems.

    :param input_data: An object containing the PID of the process to kill.
    :type input_data: KillProcessInput
    :return: A string indicating the success or failure of the operation.
    :rtype: str
    """
    pid_to_kill = str(input_data.pid)
    logger.info(f"Attempting to kill local PID: {pid_to_kill}")
    try:
        # Using a direct command instead of shell=True is safer here.
        result = subprocess.run(
            ["kill", "-9", pid_to_kill],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        if result.returncode == 0:
            logger.info(f"Successfully sent SIGKILL to PID {pid_to_kill}")
            return f"Successfully killed process {pid_to_kill}"
        else:
            error_message = result.stderr or result.stdout
            logger.error(f"Failed to kill PID {pid_to_kill}: {error_message}")
            return f"Kill command failed: {error_message}"
    except Exception as e:
        logger.exception(f"An exception occurred while trying to kill PID {pid_to_kill}")
        return f"[ERROR] Exception occurred while killing process: {e}"


@register_tool(
    name="run_local_command",
    input_model=RunLocalCommandInput,
    description="Runs a shell command on the local machine and returns its output.",
    tags=["system", "shell", "primitive"],
    safe_mode=False,  # Executing arbitrary commands is inherently unsafe.
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
        # Using shell=True can be a security risk if the command is constructed
        # from external input, but for an agent it's often necessary.
        result = subprocess.run(
            input_data.command,
            shell=input_data.shell,
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )
        output = result.stdout.strip()
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr.strip()}"
        return output
    except Exception as e:
        logger.exception(f"Exception during local command execution: {input_data.command}")
        return f"[ERROR] Command execution failed: {e}"


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
    :return: A formatted string of memory statistics (Total, Available, Used, etc.).
    :rtype: str
    """
    try:
        mem = psutil.virtual_memory()
        # Formatting to gigabytes for readability
        to_gb = lambda x: f"{x / (1024 ** 3):.2f} GB"
        result = (
            f"Total: {to_gb(mem.total)}\n"
            f"Available: {to_gb(mem.available)}\n"
            f"Used: {to_gb(mem.used)} (Percent: {mem.percent}%)"
        )
        logger.info("Memory stats retrieved successfully via psutil.")
        return result
    except Exception as e:
        logger.warning(f"psutil failed to get memory info: {e}. Is psutil installed?")
        return "[ERROR] Could not retrieve memory info. psutil might be missing or failed."


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
    """Reads raw bytes from the OS's entropy source (/dev/random) and hex-encodes them.

    :param input_data: An object specifying the number of bytes to read.
    :type input_data: GetRandomBytesInput
    :return: A hex-encoded string of random data.
    :rtype: str
    """
    try:
        with open("/dev/random", "rb") as f:
            return f.read(input_data.length).hex()
    except Exception as e:
        logger.exception("Failed to read from /dev/random")
        return f"[ERROR] Could not read random bytes: {e}"
