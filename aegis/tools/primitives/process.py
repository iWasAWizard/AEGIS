# aegis/tools/primitives/process.py
"""
Primitive tools for interacting with local system processes and resources.

This module provides tools for listing running processes and querying
resource usage, such as disk space, on the local machine.
"""

import psutil
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class ListProcessesInput(BaseModel):
    """Input model for listing system processes. Takes no arguments."""

    pass


class GetDiskUsageInput(BaseModel):
    """Input model for getting disk usage of a specific path."""

    path: str = Field(
        "/",
        description="The path of the mount point to check (e.g., '/', '/mnt/data').",
    )


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
    """
    logger.info("Listing all running processes using psutil.")
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "username"]):
            procs.append(
                f"PID: {p.info['pid']:<6} | User: {p.info['username']:<15} | Name: {p.info['name']}"
            )
        return "\n".join(procs) if procs else "No processes found."
    except Exception as e:
        logger.exception("Failed to list processes using psutil.")
        return f"[ERROR] Could not list processes: {e}"


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
    """
    path = input_data.path
    logger.info(f"Getting disk usage for path: {path}")
    try:
        usage = psutil.disk_usage(path)
        to_gb = lambda x: f"{x / (1024 ** 3):.2f} GB"
        return (
            f"Disk Usage for '{path}':\n"
            f"  - Total: {to_gb(usage.total)}\n"
            f"  - Used:  {to_gb(usage.used)} ({usage.percent}%)\n"
            f"  - Free:  {to_gb(usage.free)}"
        )
    except FileNotFoundError:
        error_msg = f"[ERROR] Path not found: {path}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        logger.exception(f"Failed to get disk usage for {path}.")
        return f"[ERROR] Could not get disk usage for '{path}': {e}"
