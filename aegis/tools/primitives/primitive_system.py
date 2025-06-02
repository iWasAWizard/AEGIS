"""
Primitive tools for accessing system information and executing shell-level diagnostics.

Includes hardware stats, uptime, OS detection, and other low-level introspection tools.
"""
import shlex
import subprocess
from typing import Optional

import psutil
from pydantic import BaseModel, Field

from aegis.models.tool_inputs import CommandWithArgsInput
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def sanitize_shell_input(command: str) -> str:
    """
    Escape untrusted input for safe shell usage.
    """
    return shlex.quote(command)


# === Input Models ===


class KillProcessInput(BaseModel):
    pid: int = Field(description="Process ID to kill.")


class GetLocalMemoryInfoInput(BaseModel):
    pass


class SimpleShellCommandInput(BaseModel):
    extra_args: Optional[str] = Field(
        default="", description="Extra arguments to pass to the command."
    )


class RunLocalCommandInput(BaseModel):
    command: str = Field(description="The shell command to execute locally.")
    shell: bool = Field(
        default=True, description="Whether to use shell execution mode."
    )


class RunCommandWithTimeoutInput(BaseModel):
    command: str = Field(..., description="The command string to run.")
    timeout: int = Field(
        default=10, description="Maximum time (in seconds) to allow the command to run."
    )
    shell: bool = Field(
        default=False, description="Whether to use shell execution (e.g., for piping)."
    )


class GetRandomStringInput(BaseModel):
    length: int = Field(
        default=32, description="Number of bytes to read from /dev/random."
    )


# === Tools ===


@register_tool(
    name="kill_local_process",
    input_model=KillProcessInput,
    description="Kills a local process by its PID using SIGKILL (-9).",
    tags=["system", "process", "primitive"],
    safe_mode=False,
    category="primitive",
)
def kill_local_process(input_data: KillProcessInput) -> str:
    """
    Executes `kill -9` on the given PID. Works on Unix-based systems.
    """
    logger.info(f"[kill_local_process] Attempting to kill PID: {input_data.pid}")
    try:
        result = subprocess.run(
            ["kill", "-9", str(input_data.pid)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info(
                f"[kill_local_process] Successfully killed PID {input_data.pid}"
            )
            return f"Successfully killed process {input_data.pid}"
        else:
            logger.error(f"[kill_local_process] Error: {result.stderr.strip()}")
            return f"Kill failed: {result.stderr.strip() or result.stdout.strip()}"
    except Exception as e:
        logger.exception(f"[kill_local_process] Exception: {e}")
        return f"Exception occurred while killing process: {e}"


@register_tool(
    name="list_block_devices",
    input_model=CommandWithArgsInput,
    tags=["block", "hardware", "primitive"],
    description="Run lsblk to list block devices and partitions.",
    safe_mode=True,
    purpose="Show attached block devices and their mount points.",
    category="system",
)
def list_block_devices(input_data: CommandWithArgsInput) -> str:
    logger.info("Listing block devices using lsblk")
    try:
        result = subprocess.run(
            f"lsblk {input_data.extra_args}".strip().split(),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"[ERROR] lsblk failed: {str(e)}"


@register_tool(
    name="run_local_command",
    input_model=RunLocalCommandInput,
    description="Runs a shell command locally and returns output. Shell mode enabled by default.",
    tags=["system", "shell", "primitive"],
    safe_mode=False,
    category="primitive",
)
def run_local_command(input_data: RunLocalCommandInput) -> str:
    """
    Executes the given shell command locally using subprocess.
    """
    logger.info(f"[run_local_command] Executing: {input_data.command}")
    try:
        result = subprocess.run(
            input_data.command,
            shell=input_data.shell,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info(f"[run_local_command] Success")
            return result.stdout.strip()
        else:
            logger.error(
                f"[run_local_command] Failed with stderr: {result.stderr.strip()}"
            )
            return f"Error: {result.stderr.strip() or result.stdout.strip()}"
    except Exception as e:
        logger.exception(f"[run_local_command] Exception during execution: {e}")
        return f"Execution failed: {e}"


@register_tool(
    name="get_local_memory_info",
    input_model=GetLocalMemoryInfoInput,
    description="Returns local memory usage statistics using psutil or shell fallback.",
    tags=["system", "memory", "introspection"],
    safe_mode=True,
    category="primitive",
)
def get_local_memory_info(_: GetLocalMemoryInfoInput) -> str:
    """
    Uses psutil to return memory stats, or falls back to shell command.
    """
    try:
        mem = psutil.virtual_memory()
        result = (
            f"Total: {mem.total / (1024 ** 3):.2f} GB\n"
            f"Available: {mem.available / (1024 ** 3):.2f} GB\n"
            f"Used: {mem.used / (1024 ** 3):.2f} GB\n"
            f"Free: {mem.free / (1024 ** 3):.2f} GB\n"
            f"Percent Used: {mem.percent}%"
        )
        logger.info("[get_local_memory_info] Memory stats retrieved via psutil")
        return result
    except Exception as e:
        logger.warning(f"[get_local_memory_info] psutil failed: {e}")
        return "psutil not available or failed. Consider installing psutil or using shell fallback."


@register_tool(
    name="run_command_with_timeout",
    input_model=RunCommandWithTimeoutInput,
    description="Execute a system command with a timeout and optional shell mode.",
    tags=["system", "primitive"],
    safe_mode=False,
    timeout=15,
    retries=0,
    category="primitive",
)
def run_command_with_timeout(input_data: RunCommandWithTimeoutInput) -> str:
    """
    Executes the given command using subprocess with timeout control.
    """
    try:
        result = subprocess.run(
            input_data.command,
            shell=input_data.shell,
            capture_output=True,
            timeout=input_data.timeout,
            text=True,
        )
        return (
            f"✅ Command completed with exit code {result.returncode}\n"
            f"--- STDOUT ---\n{result.stdout.strip()}\n"
            f"--- STDERR ---\n{result.stderr.strip()}"
        )
    except subprocess.TimeoutExpired as e:
        return (
            f"⏰ Timeout: Command exceeded {input_data.timeout}s\n"
            f"--- STDOUT ---\n{e.stdout or ''}\n"
            f"--- STDERR ---\n{e.stderr or ''}"
        )
    except Exception as e:
        return f"❌ Command failed: {str(e)}"


@register_tool(
    name="get_random_string",
    input_model=GetRandomStringInput,
    description="Returns a string of complete gibberish from /dev/random.",
    tags=["system", "primitive"],
    safe_mode=True,
    category="primitive",
)
def get_random_string(input_data: GetRandomStringInput) -> str:
    """
    Reads raw bytes from /dev/random and returns them as a hex string.
    """
    try:
        with open("/dev/random", "rb") as f:
            return f.read(input_data.length).hex()
    except Exception as e:
        logger.exception("[get_random_string] Failed to read from /dev/random")
        return f"[ERROR] Could not read random bytes: {e}"
