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

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import MachineFileInput
from aegis.utils.logger import setup_logger
from aegis.utils.machine_loader import get_machine

logger = setup_logger(__name__)


# === Input Models ===


class RetrieveRemoteLogFileInput(MachineFileInput):
    """Input for retrieving a remote log file to a local destination.

    :ivar local_destination: The local path to save the downloaded file.
    :vartype local_destination: str
    """

    local_destination: str = Field(
        ..., description="The local path to save the downloaded file."
    )


class BackupRemoteFileInput(MachineFileInput):
    """Input for creating a .bak backup of a file on a remote host."""

    pass


class InjectLineIntoConfigInput(MachineFileInput):
    """Input for appending a single line of text to a remote file.

    :ivar line: The line of text to inject into the file.
    :vartype line: str
    """

    line: str = Field(..., description="The line of text to inject into the file.")


class DiffLocalFileAfterEditInput(BaseModel):
    """Input for diffing a local file before and after an in-place edit.

    :ivar file_path: The path to the local file to edit and diff.
    :vartype file_path: str
    :ivar replacement_text: The new text to completely overwrite the file with.
    :vartype replacement_text: str
    """

    file_path: str = Field(
        ..., description="The path to the local file to edit and diff."
    )
    replacement_text: str = Field(
        ..., description="The new text to completely overwrite the file with."
    )


class DiffRemoteFileAfterEditInput(MachineFileInput):
    """Input for diffing a remote file before and after an in-place edit.

    :ivar new_contents: The new text to completely overwrite the remote file with.
    :vartype new_contents: str
    """

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

    :param input_data: An object containing the machine name, remote path, and local destination.
    :type input_data: RetrieveRemoteLogFileInput
    :return: The result of the download operation.
    :rtype: str
    """
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.download(
        remote_path=input_data.file_path, local_path=input_data.local_destination
    )


@register_tool(
    name="check_and_read_config_file",
    input_model=MachineFileInput,
    tags=["ssh", "file", "config", "wrapper"],
    description="Reads a remote configuration file, but only if it exists.",
    safe_mode=True,
    purpose="Safely read a remote config file without causing an error if it's missing.",
    category="file_ops",
)
def check_and_read_config_file(input_data: MachineFileInput) -> str:
    """Checks for a remote file's existence and, if present, returns its contents.

    :param input_data: An object containing the machine name and remote file path.
    :type input_data: MachineFileInput
    :return: The file contents or an informational message if the file is missing.
    :rtype: str
    """
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
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

    :param input_data: An object containing the machine name and remote file path.
    :type input_data: BackupRemoteFileInput
    :return: The result of the copy command or an informational message.
    :rtype: str
    """
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    if not executor.check_file_exists(input_data.file_path):
        return f"[INFO] File '{input_data.file_path}' does not exist. Skipping backup."

    backup_cmd = f"cp {shlex.quote(input_data.file_path)} {shlex.quote(input_data.file_path + '.bak')}"
    executor.run(f"sudo {backup_cmd}")
    return f"Successfully created backup: {input_data.file_path}.bak"


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

    :param input_data: An object containing the machine name, file path, and line to inject.
    :type input_data: InjectLineIntoConfigInput
    :return: The output of the `tee` command (often empty) or a success message.
    :rtype: str
    """
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    append_cmd = f"echo {shlex.quote(input_data.line)} | sudo tee -a {shlex.quote(input_data.file_path)}"
    executor.run(append_cmd)
    return f"Successfully injected line into {input_data.file_path}"


@register_tool(
    name="diff_local_file_after_edit",
    input_model=DiffLocalFileAfterEditInput,
    tags=["local", "file", "edit", "diff", "wrapper"],
    description="Reads a local file, overwrites it with new text, and returns a diff of the changes.",
    safe_mode=False,
    purpose="Compare local file contents before and after an in-place replacement.",
    category="file_ops",
)
def diff_local_file_after_edit(input_data: DiffLocalFileAfterEditInput) -> str:
    """Performs an in-place edit of a local file and returns a diff of the changes.

    :param input_data: An object containing the local file path and new content.
    :type input_data: DiffLocalFileAfterEditInput
    :return: A unified diff of the changes or an error message.
    :rtype: str
    """
    try:
        file_path = Path(input_data.file_path)
        if not file_path.is_file():
            raise ToolExecutionError(f"Local file not found: {file_path}")

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
        raise ToolExecutionError(f"Failed to edit and diff local file: {e}")


@register_tool(
    name="diff_remote_file_after_edit",
    input_model=DiffRemoteFileAfterEditInput,
    tags=["remote", "file", "edit", "diff", "wrapper"],
    description="Reads a remote file, overwrites it with new text, and returns a diff.",
    safe_mode=True,
    purpose="Compare remote file contents before and after an in-place replacement.",
    category="file_ops",
)
def diff_remote_file_after_edit(input_data: DiffRemoteFileAfterEditInput) -> str:
    """Performs an in-place edit of a remote file and returns a diff of the changes.

    This tool reads the original content, overwrites the remote file with new
    content, and then generates a diff of the changes locally.

    :param input_data: An object containing machine name, remote path, and new content.
    :type input_data: DiffRemoteFileAfterEditInput
    :return: A unified diff of the changes or an error message.
    :rtype: str
    """
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)

    # 1. Read the original contents.
    original_contents = executor.run(f"cat {shlex.quote(input_data.file_path)}")

    # 2. Write the new contents.
    echo_cmd = f"echo {shlex.quote(input_data.new_contents)} | sudo tee {shlex.quote(input_data.file_path)} > /dev/null"
    executor.run(echo_cmd)

    # 3. Generate the diff locally.
    diff = difflib.unified_diff(
        original_contents.splitlines(),
        input_data.new_contents.splitlines(),
        fromfile=f"{input_data.file_path} (before)",
        tofile=f"{input_data.file_path} (after)",
        lineterm="",
    )
    return "\n".join(diff) or "Remote file content was identical; no changes made."
