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
