# aegis/tools/primitives/primitive_filesystem.py
"""
Primitive tools for interacting with local and remote filesystems.

This module provides the fundamental building blocks for file operations,
such as transferring files via SCP, reading remote file contents, and
creating files of a specific size.
"""

import difflib
import re
import shlex

from pydantic import BaseModel, Field

from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import MachineFileInput, MachineTargetInput
from aegis.tools.primitives.primitive_system import run_local_command, RunLocalCommandInput
from aegis.utils.logger import setup_logger
from aegis.utils.machine_loader import get_machine

logger = setup_logger(__name__)


# === Input Models ===


class CreateRandomFileInput(BaseModel):
    """Input for creating a file of a specific size with random data.

    :ivar file_path: The full path where the new file will be created.
    :vartype file_path: str
    :ivar size: The desired size of the file. Supports shorthands like '10k', '25M', '1G'.
                Defaults to bytes if no suffix is given.
    :vartype size: str
    """
    file_path: str = Field(..., description="The full path where the new file will be created.")
    size: str = Field(...,
                      description="The desired size of the file. Supports shorthands like '10k', '25M', '1G'. Defaults to bytes if no suffix is given.")


class TransferFileToRemoteInput(MachineFileInput):
    """Input model for transferring a local file to a remote host.

    :ivar source_path: Path to the local file to transfer.
    :vartype source_path: str
    :ivar destination_path: Destination path on the remote machine.
    :vartype destination_path: str
    """
    source_path: str = Field(..., description="Path to the local file to transfer.")
    destination_path: str = Field(..., description="Destination path on the remote machine.")


class FetchFileFromRemoteInput(MachineFileInput):
    """Input model for fetching a file from a remote host.

    :ivar local_path: Destination path on the local machine.
    :vartype local_path: str
    """
    local_path: str = Field(..., description="Destination path on the local machine.")


class RunRemoteScriptInput(MachineFileInput):
    """Input model for uploading and executing a script on a remote host.

    :ivar script_path: Local path to the shell script to send and execute.
    :vartype script_path: str
    :ivar remote_path: Destination path on the remote machine.
    :vartype remote_path: str
    """
    script_path: str = Field(..., description="Local path to the shell script to send and execute.")
    remote_path: str = Field(..., description="Destination path on the remote machine.")


class AppendToRemoteFileInput(MachineFileInput):
    """Input model for appending text to a remote file.

    :ivar content: Text to append to the file.
    :vartype content: str
    """
    content: str = Field(..., description="Text to append to the file.")


class GetRemoteDirectoryListingInput(MachineTargetInput):
    """Input model for listing the contents of a remote directory.

    :ivar directory_path: Directory path to list.
    :vartype directory_path: str
    """
    directory_path: str = Field(..., description="Directory path to list.")


class DiffTextBlocksInput(BaseModel):
    """Input model for generating a diff between two blocks of text.

    :ivar old: Original block of text.
    :vartype old: str
    :ivar new: New block of text.
    :vartype new: str
    """
    old: str = Field(..., description="Original block of text.")
    new: str = Field(..., description="New block of text.")


# === Tools ===

@register_tool(
    name="create_random_file",
    input_model=CreateRandomFileInput,
    tags=["file", "local", "generate", "primitive"],
    description="Creates a local file of a specified size filled with random data from /dev/urandom.",
    safe_mode=False,
    purpose="Generate a test file of a specific size.",
    category="file_ops",
)
def create_random_file(input_data: CreateRandomFileInput) -> str:
    """Creates a file of a given size using the 'dd' command.

    Parses a size string with suffixes (k, M, G, etc.) to construct the
    appropriate dd command to generate a file from /dev/urandom.

    :param input_data: An object containing the file path and size string.
    :type input_data: CreateRandomFileInput
    :return: The output of the dd command execution.
    :rtype: str
    """
    logger.info(f"Request to create file '{input_data.file_path}' with size '{input_data.size}'")

    size_str = input_data.size.lower().strip()
    match = re.match(r'^(\d+)([kmgtp]?)b?$', size_str)

    if not match:
        return f"[ERROR] Invalid size format: '{input_data.size}'. Use a number with an optional suffix (k, M, G, T, P)."

    value = int(match.group(1))
    suffix = match.group(2)

    # We use bs=1k and adjust the count to be friendlier to most filesystems
    block_size = "1K"
    count = 0

    if not suffix:  # bytes
        count = (value + 1023) // 1024  # Round up to nearest KB
    elif suffix == 'k':
        count = value
    elif suffix == 'm':
        count = value * 1024
    elif suffix == 'g':
        count = value * 1024 * 1024
    elif suffix == 't':
        count = value * 1024 * 1024 * 1024
    elif suffix == 'p':
        count = value * 1024 * 1024 * 1024 * 1024

    if count == 0 and value > 0:
        # Handle cases for very small byte sizes
        block_size = str(value)
        count = 1

    command = f"dd if=/dev/urandom of={shlex.quote(input_data.file_path)} bs={block_size} count={count}"

    logger.info(f"Executing command: {command}")
    return run_local_command(RunLocalCommandInput(command=command, shell=True))


@register_tool(
    name="transfer_file_to_remote",
    input_model=TransferFileToRemoteInput,
    tags=["ssh", "scp", "remote", "file", "primitive"],
    description="Transfer a file from the local system to a remote machine via SCP.",
    safe_mode=True,
    purpose="Transfer a local file to a remote system using SCP",
    category="file_ops",
)
def transfer_file_to_remote(input_data: TransferFileToRemoteInput) -> str:
    """Transfers a local file to a remote machine using the SSHExecutor.

    :param input_data: An object containing machine name, source path, and destination path.
    :type input_data: TransferFileToRemoteInput
    :return: The result of the upload operation.
    :rtype: str
    """
    logger.info(f"Transferring '{input_data.source_path}' to '{input_data.machine_name}:{input_data.destination_path}'")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.upload(input_data.source_path, input_data.destination_path)


@register_tool(
    name="fetch_file_from_remote",
    input_model=FetchFileFromRemoteInput,
    tags=["ssh", "scp", "remote", "file", "primitive"],
    description="Download a file from a remote machine to the local system via SCP.",
    safe_mode=True,
    purpose="Download a specific file from a remote host",
    category="file_ops",
)
def fetch_file_from_remote(input_data: FetchFileFromRemoteInput) -> str:
    """Fetches a file from a remote machine using the SSHExecutor.

    :param input_data: An object containing machine name, remote path, and local path.
    :type input_data: FetchFileFromRemoteInput
    :return: The result of the download operation.
    :rtype: str
    """
    logger.info(f"Fetching '{input_data.machine_name}:{input_data.file_path}' to '{input_data.local_path}'")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.download(input_data.file_path, input_data.local_path)


@register_tool(
    name="read_remote_file",
    input_model=MachineFileInput,
    tags=["ssh", "remote", "file", "read", "primitive"],
    description="Read the contents of a file on a remote system.",
    safe_mode=True,
    purpose="Read and return the contents of a remote file",
    category="file_ops",
)
def read_remote_file(input_data: MachineFileInput) -> str:
    """Reads the content of a remote file using `cat` via the SSHExecutor.

    :param input_data: An object containing the machine name and remote file path.
    :type input_data: MachineFileInput
    :return: The contents of the remote file.
    :rtype: str
    """
    logger.info(f"Reading remote file '{input_data.file_path}' from machine '{input_data.machine_name}'")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run(f"cat {shlex.quote(input_data.file_path)}")


@register_tool(
    name="check_remote_file_exists",
    input_model=MachineFileInput,
    tags=["ssh", "remote", "file", "check", "primitive"],
    description="Check if a specific file exists on a remote system.",
    safe_mode=True,
    purpose="Determine if a specific file exists on a remote machine",
    category="file_ops",
)
def check_remote_file_exists(input_data: MachineFileInput) -> str:
    """Checks if a file exists on a remote machine using the SSHExecutor.

    :param input_data: An object containing the machine name and remote file path.
    :type input_data: MachineFileInput
    :return: "Exists" if the file is found, "Missing" otherwise.
    :rtype: str
    """
    logger.info(f"Checking for remote file '{input_data.file_path}' on machine '{input_data.machine_name}'")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return "Exists" if executor.check_file_exists(input_data.file_path) else "Missing"


@register_tool(
    name="run_remote_script",
    input_model=RunRemoteScriptInput,
    tags=["ssh", "scp", "remote", "script", "primitive"],
    description="Upload a local script to a remote host and execute it.",
    safe_mode=True,
    purpose="Upload and execute a local script on a remote machine",
    category="system",
)
def run_remote_script(input_data: RunRemoteScriptInput) -> str:
    """Uploads and executes a script on a remote machine.

    :param input_data: An object containing machine name, local script path, and remote destination path.
    :type input_data: RunRemoteScriptInput
    :return: The output of the script execution, or an error if the upload fails.
    :rtype: str
    """
    logger.info(f"Uploading and running script '{input_data.script_path}' on machine '{input_data.machine_name}'")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    upload_result = executor.upload(input_data.script_path, input_data.remote_path)
    if "[ERROR]" in upload_result:
        return f"[ERROR] Script upload failed: {upload_result}"
    return executor.run(f"bash {shlex.quote(input_data.remote_path)}")


@register_tool(
    name="append_to_remote_file",
    input_model=AppendToRemoteFileInput,
    tags=["ssh", "remote", "file", "append", "primitive"],
    description="Append a line of text to a file on a remote machine.",
    safe_mode=True,
    purpose="Append text to a remote file via SSH",
    category="file_ops",
)
def append_to_remote_file(input_data: AppendToRemoteFileInput) -> str:
    """Appends content to a remote file using `echo` and `tee`.

    :param input_data: An object containing machine name, file path, and content to append.
    :type input_data: AppendToRemoteFileInput
    :return: The output of the remote command.
    :rtype: str
    """
    logger.info(f"Appending content to '{input_data.file_path}' on machine '{input_data.machine_name}'")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    cmd = f"echo {shlex.quote(input_data.content)} | sudo tee -a {shlex.quote(input_data.file_path)}"
    return executor.run(cmd)


@register_tool(
    name="get_remote_directory_listing",
    input_model=GetRemoteDirectoryListingInput,
    tags=["ssh", "remote", "directory", "list", "primitive"],
    description="List contents of a directory on a remote machine.",
    safe_mode=True,
    purpose="List the contents of a remote directory using 'ls -la'",
    category="file_ops",
)
def get_remote_directory_listing(input_data: GetRemoteDirectoryListingInput) -> str:
    """Lists the contents of a remote directory using `ls -la`.

    :param input_data: An object containing the machine name and directory path.
    :type input_data: GetRemoteDirectoryListingInput
    :return: The formatted directory listing from the remote host.
    :rtype: str
    """
    logger.info(f"Listing directory '{input_data.directory_path}' on machine '{input_data.machine_name}'")
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    return executor.run(f"ls -la {shlex.quote(input_data.directory_path)}")


@register_tool(
    name="diff_text_blocks",
    input_model=DiffTextBlocksInput,
    tags=["diff", "text", "primitive"],
    description="Generate a unified diff between two blocks of text.",
    safe_mode=True,
    purpose="Generate a unified diff between two blocks of text",
    category="file_ops",
)
def diff_text_blocks(input_data: DiffTextBlocksInput) -> str:
    """Generates a unified diff between two strings.

    :param input_data: An object containing the 'old' and 'new' text blocks.
    :type input_data: DiffTextBlocksInput
    :return: A string containing the unified diff.
    :rtype: str
    """
    logger.info("Generating diff between two text blocks")
    old_lines = input_data.old.strip().splitlines()
    new_lines = input_data.new.strip().splitlines()
    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile="old", tofile="new", lineterm=""
    )
    return "\n".join(diff)
