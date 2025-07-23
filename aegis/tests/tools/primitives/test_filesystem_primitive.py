# aegis/tests/tools/primitives/test_filesystem_primitive.py
"""
Unit tests for the filesystem primitive tools.
"""

import difflib
import re
import shlex

from pydantic import BaseModel, Field

from aegis.executors.ssh_exec import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import MachineFileInput, MachineTargetInput
from aegis.tools.primitives.primitive_system import (
    run_local_command,
    RunLocalCommandInput,
)
from aegis.utils.logger import setup_logger
from aegis.utils.machine_loader import get_machine

logger = setup_logger(__name__)


# === Input Models ===


class TransferFileToRemoteInput(MachineFileInput):
    """Input model for transferring a local file to a remote host.

    :ivar source_path: Path to the local file to transfer.
    :vartype source_path: str
    :ivar destination_path: Destination path on the remote machine.
    :vartype destination_path: str
    """

    source_path: str = Field(..., description="Path to the local file to transfer.")
    destination_path: str = Field(
        ..., description="Destination path on the remote machine."
    )


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

    script_path: str = Field(
        ..., description="Local path to the shell script to send and execute."
    )
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


# === Tools ===


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
    logger.info(
        f"Transferring '{input_data.source_path}' to '{input_data.machine_name}:{input_data.destination_path}'"
    )
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
    logger.info(
        f"Fetching '{input_data.machine_name}:{input_data.file_path}' to '{input_data.local_path}'"
    )
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
    logger.info(
        f"Reading remote file '{input_data.file_path}' from machine '{input_data.machine_name}'"
    )
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    output = executor.run(f"cat {shlex.quote(input_data.file_path)}")
    return output


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
    logger.info(
        f"Checking for remote file '{input_data.file_path}' on machine '{input_data.machine_name}'"
    )
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
    logger.info(
        f"Uploading and running script '{input_data.script_path}' on machine '{input_data.machine_name}'"
    )
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    executor.upload(input_data.script_path, input_data.remote_path)
    output = executor.run(f"bash {shlex.quote(input_data.remote_path)}")
    return output


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
    logger.info(
        f"Appending content to '{input_data.file_path}' on machine '{input_data.machine_name}'"
    )
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    cmd = f"echo {shlex.quote(input_data.content)} | sudo tee -a {shlex.quote(input_data.file_path)}"
    output = executor.run(cmd)
    return output


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
    logger.info(
        f"Listing directory '{input_data.directory_path}' on machine '{input_data.machine_name}'"
    )
    machine = get_machine(input_data.machine_name)
    executor = SSHExecutor(machine)
    output = executor.run(f"ls -la {shlex.quote(input_data.directory_path)}")
    return output