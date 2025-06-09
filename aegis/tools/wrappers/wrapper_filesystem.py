# aegis/tools/wrappers/wrapper_filesystem.py
"""
Filesystem wrapper tools for higher-level, multi-step file operations.

This module provides tools that compose multiple actions to achieve a specific
goal, such as backing up a file before modifying it, or checking for a file's
existence before attempting to read it.
"""

import difflib
import shlex
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import RemoteFileInput
from aegis.utils.host_utils import get_user_host_from_string
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class RetrieveRemoteLogFileInput(RemoteFileInput):
    """Input for retrieving a remote log file to a local destination."""

    local_destination: str = Field(
        ..., description="The local path to save the downloaded file."
    )


class BackupRemoteFileInput(RemoteFileInput):
    """Input for creating a .bak backup of a file on a remote host."""

    pass


class InjectLineIntoConfigInput(RemoteFileInput):
    """Input for appending a single line of text to a remote file."""

    line: str = Field(..., description="The line of text to inject into the file.")


class DiffLocalFileAfterEditInput(BaseModel):
    """Input for diffing a local file before and after an in-place edit."""

    file_path: str = Field(
        ..., description="The path to the local file to edit and diff."
    )
    replacement_text: str = Field(
        ..., description="The new text to completely overwrite the file with."
    )


class DiffRemoteFileAfterEditInput(RemoteFileInput):
    """Input for diffing a remote file before and after an in-place edit."""

    new_contents: str = Field(
        ..., description="The new text to completely overwrite the remote file with."
    )


# === Tools ===


@register_tool(
    name="retrieve_remote_log_file",
    input_model=RetrieveRemoteLogFileInput,
    tags=["ssh", "scp", "log", "wrapper"],
    description="Downloads a specific log file from a remote system to a local path.",
    safe_mode=True,
    purpose="Download a log file from a remote machine.",
    category="file_ops",
)
def retrieve_remote_log_file(input_data: RetrieveRemoteLogFileInput) -> str:
    """A specific wrapper to download a file, intended for log retrieval.

    :param input_data: An object containing remote host, remote path, and local destination.
    :type input_data: RetrieveRemoteLogFileInput
    :return: A status message indicating the result of the download.
    :rtype: str
    """
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.download(
        remote_path=input_data.file_path, local_path=input_data.local_destination
    )


@register_tool(
    name="check_and_read_config_file",
    input_model=RemoteFileInput,
    tags=["ssh", "file", "config", "wrapper"],
    description="Reads a remote configuration file, but only if it exists.",
    safe_mode=True,
    purpose="Safely read a remote config file without causing an error if it's missing.",
    category="file_ops",
)
def check_and_read_config_file(input_data: RemoteFileInput) -> str:
    """Checks for a remote file's existence and, if present, returns its contents.

    :param input_data: An object containing the host and file path to check and read.
    :type input_data: RemoteFileInput
    :return: The file's contents, or an informational message if it's missing.
    :rtype: str
    """
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    if executor.check_file_exists(input_data.file_path):
        return executor.run(f"cat {shlex.quote(input_data.file_path)}")
    else:
        return f"[INFO] File does not exist at '{input_data.file_path}', so it cannot be read."


@register_tool(
    name="backup_remote_file",
    input_model=BackupRemoteFileInput,
    tags=["ssh", "backup", "file", "wrapper"],
    description="Creates a backup of a remote file by copying it to a `.bak` version.",
    safe_mode=True,
    purpose="Create a .bak backup of a remote file before modification.",
    category="file_ops",
)
def backup_remote_file(input_data: BackupRemoteFileInput) -> str:
    """Creates a `.bak` copy of a specified file on a remote system if it exists.

    :param input_data: An object containing the host and file path to back up.
    :type input_data: BackupRemoteFileInput
    :return: The result of the 'cp' command or an informational message.
    :rtype: str
    """
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    if not executor.check_file_exists(input_data.file_path):
        return f"[INFO] File '{input_data.file_path}' does not exist. Skipping backup."

    backup_cmd = f"cp {shlex.quote(input_data.file_path)} {shlex.quote(input_data.file_path + '.bak')}"
    return executor.run(f"sudo {backup_cmd}")


@register_tool(
    name="inject_line_into_config",
    input_model=InjectLineIntoConfigInput,
    tags=["ssh", "config", "append", "wrapper"],
    description="Appends a single line of text to a remote configuration file.",
    safe_mode=True,
    purpose="Append a line of configuration to a remote file.",
    category="file_ops",
)
def inject_line_into_config(input_data: InjectLineIntoConfigInput) -> str:
    """Appends a line to a remote file, often used for configuration changes.

    :param input_data: An object with host, file path, and the line of content to add.
    :type input_data: InjectLineIntoConfigInput
    :return: The output of the remote command.
    :rtype: str
    """
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    append_cmd = f"echo {shlex.quote(input_data.line)} | sudo tee -a {shlex.quote(input_data.file_path)}"
    return executor.run(append_cmd)


@register_tool(
    name="diff_local_file_after_edit",
    input_model=DiffLocalFileAfterEditInput,
    tags=["local", "file", "edit", "diff", "wrapper"],
    description="Reads a local file, overwrites it with new text, and returns a diff of the changes.",
    safe_mode=False,  # Modifies a local file.
    purpose="Compare local file contents before and after an in-place replacement.",
    category="file_ops",
)
def diff_local_file_after_edit(input_data: DiffLocalFileAfterEditInput) -> str:
    """Performs an in-place edit of a local file and returns a diff of the changes.

    :param input_data: An object with the local file path and the new text.
    :type input_data: DiffLocalFileAfterEditInput
    :return: A unified diff string of the changes made.
    :rtype: str
    """
    try:
        file_path = Path(input_data.file_path)
        if not file_path.is_file():
            return f"[ERROR] Local file not found: {file_path}"

        original_content = file_path.read_text(encoding="utf-8")
        file_path.write_text(input_data.replacement_text, encoding="utf-8")

        diff = difflib.unified_diff(
            original_content.splitlines(),
            input_data.replacement_text.splitlines(),
            fromfile=f"{file_path.name} (before)",
            tofile=f"{file_path.name} (after)",
            lineterm="",
        )
        return "\n".join(diff) or "File content was identical; no changes made."
    except Exception as e:
        logger.exception(f"Failed to edit and diff local file: {input_data.file_path}")
        return f"[ERROR] Failed to edit and diff local file: {e}"


@register_tool(
    name="diff_remote_file_after_edit",
    input_model=DiffRemoteFileAfterEditInput,
    tags=["remote", "file", "edit", "diff", "wrapper"],
    description="Reads a remote file, overwrites it with new text, and returns a diff.",
    safe_mode=True,  # Remote changes are contained.
    purpose="Compare remote file contents before and after an in-place replacement.",
    category="file_ops",
)
def diff_remote_file_after_edit(input_data: DiffRemoteFileAfterEditInput) -> str:
    """Performs an in-place edit of a remote file and returns a diff of the changes.

    :param input_data: An object with host, file path, and the new file contents.
    :type input_data: DiffRemoteFileAfterEditInput
    :return: A unified diff string of the changes made to the remote file.
    :rtype: str
    """
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)

    # 1. Read the original contents.
    original_contents = executor.run(f"cat {shlex.quote(input_data.file_path)}")
    if "[ERROR]" in original_contents or "[STDERR]" in original_contents:
        return f"[ERROR] Could not read original remote file to create diff: {original_contents}"

    # 2. Write the new contents.
    echo_cmd = f"echo {shlex.quote(input_data.new_contents)} | sudo tee {shlex.quote(input_data.file_path)}"
    write_result = executor.run(echo_cmd)
    if "[ERROR]" in write_result or "[STDERR]" in write_result:
        return f"[ERROR] Could not write new content to remote file: {write_result}"

    # 3. Generate the diff locally.
    diff = difflib.unified_diff(
        original_contents.splitlines(),
        input_data.new_contents.splitlines(),
        fromfile=f"{input_data.file_path} (before)",
        tofile=f"{input_data.file_path} (after)",
        lineterm="",
    )
    return "\n".join(diff) or "Remote file content was identical; no changes made."
