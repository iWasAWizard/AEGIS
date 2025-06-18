# aegis/tools/primitives/process.py
"""
Primitive tools for interacting with local system processes and resources.

This module provides tools for listing running processes and querying
resource usage, such as disk space, on the local machine. These rely on the
`psutil` library for cross-platform compatibility.
"""

import psutil
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class ListProcessesInput(BaseModel):
    """Input model for listing system processes. Takes no arguments."""

    pass


class GetDiskUsageInput(BaseModel):
    """Input model for getting disk usage of a specific path.

    :ivar path: The path of the mount point to check (e.g., '/', '/mnt/data').
    :vartype path: str
    """

    path: str = Field(
        "/",
        description="The path of the mount point to check (e.g., '/', '/mnt/data').",
    )


def _format_bytes_to_gb(num_bytes: int) -> str:
    """Helper function to format bytes into a human-readable GB string."""
    return f"{num_bytes / (1024 ** 3):.2f} GB"


# === Tools ===


@register_tool(
    name="list_processes",
    input_model=ListProcessesInput,
    description="Lists all running processes on the local machine with their PID, name, and username.",
    tags=["system", "process", "monitoring", "primitive"],
    safe_mode=True,
    purpose="Get a list of currently running processes.",
    category="system",
)
def list_processes(_: ListProcessesInput) -> str:
    """Uses psutil to iterate over system processes and return a formatted list.

    :param _: This tool takes no arguments.
    :type _: ListProcessesInput
    :return: A formatted string listing processes, or an error message.
    :rtype: str
    :raises ToolExecutionError: If `psutil` fails to retrieve the process list.
    """
    logger.info("Listing all running processes using psutil.")
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "username"]):
            procs.append(
                f"PID: {p.pid:<6} | User: {p.username():<15} | Name: {p.name()}"  # type: ignore
            )
        return "\n".join(procs) if procs else "No processes found."
    except Exception as e:  # Catches psutil.Error, psutil.AccessDenied, etc.
        logger.exception("Failed to list processes using psutil.")
        raise ToolExecutionError(f"Could not list processes: {e}")


@register_tool(
    name="get_disk_usage",
    input_model=GetDiskUsageInput,
    description="Gets the disk usage (total, used, free) for a given filesystem path.",
    tags=["system", "disk", "monitoring", "primitive"],
    safe_mode=True,
    purpose="Check the disk space on a local mount point.",
    category="system",
)
def get_disk_usage(input_data: GetDiskUsageInput) -> str:
    """Uses psutil to get disk usage statistics for a specified path.

    :param input_data: An object containing the path to check.
    :type input_data: GetDiskUsageInput
    :return: A formatted string of disk usage statistics, or an error message.
    :rtype: str
    :raises ToolExecutionError: If `psutil` fails or the path is not found.
    """
    path = input_data.path
    logger.info(f"Getting disk usage for path: {path}")
    try:
        usage = psutil.disk_usage(path)
        return (
            f"Disk Usage for '{path}':\n"
            f"  - Total: {_format_bytes_to_gb(usage.total)}\n"
            f"  - Used:  {_format_bytes_to_gb(usage.used)} ({usage.percent}%)\n"
            f"  - Free:  {_format_bytes_to_gb(usage.free)}"
        )
    except FileNotFoundError as e:
        error_msg = f"Path not found for disk usage check: {path}"
        logger.error(f"{error_msg}: {e}")
        raise ToolExecutionError(error_msg)
    except Exception as e:  # Catches other psutil errors
        logger.exception(f"Failed to get disk usage for {path}.")
        raise ToolExecutionError(f"Could not get disk usage for '{path}': {e}")
