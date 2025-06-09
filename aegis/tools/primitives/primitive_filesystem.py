# aegis/tools/primitives/primitive_filesystem.py
"""
Primitive tools for interacting with local and remote filesystems.

This module provides the fundamental building blocks for file operations,
such as transferring files via SCP, reading remote file contents, and
checking for file existence. These tools are designed to be composed by
higher-level wrapper tools.
"""

import difflib
import shlex
from typing import Optional

from pydantic import BaseModel, Field

from aegis.executors.ssh import SSHExecutor
from aegis.registry import register_tool
from aegis.schemas.common_inputs import RemoteFileInput
from aegis.utils.host_utils import get_user_host_from_string
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class TransferFileToRemoteInput(RemoteFileInput):
    """Input model for transferring a local file to a remote host."""

    source_path: str = Field(..., description="Path to the local file to transfer.")
    destination_path: str = Field(
        ..., description="Destination path on the remote machine."
    )


class FetchFileFromRemoteInput(RemoteFileInput):
    """Input model for fetching a file from a remote host."""

    local_path: str = Field(..., description="Destination path on the local machine.")


class RunRemoteScriptInput(RemoteFileInput):
    """Input model for uploading and executing a script on a remote host."""

    script_path: str = Field(
        ..., description="Local path to the shell script to send and execute."
    )
    remote_path: str = Field(..., description="Destination path on the remote machine.")


class AppendToRemoteFileInput(RemoteFileInput):
    """Input model for appending text to a remote file."""

    content: str = Field(..., description="Text to append to the file.")


class GetRemoteDirectoryListingInput(BaseModel):
    """Input model for listing the contents of a remote directory."""

    host: str = Field(..., description="Remote host (e.g., 'user@host.com').")
    directory_path: str = Field(..., description="Directory path to list.")
    ssh_key_path: Optional[str] = Field(None, description="Path to SSH private key.")


class DiffTextBlocksInput(BaseModel):
    """Input model for generating a diff between two blocks of text."""

    old: str = Field(..., description="Original block of text.")
    new: str = Field(..., description="New block of text.")


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
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
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
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.download(input_data.remote_path, input_data.local_path)


@register_tool(
    name="read_remote_file",
    input_model=RemoteFileInput,
    tags=["ssh", "remote", "file", "read", "primitive"],
    description="Read the contents of a file on a remote system.",
    safe_mode=True,
    purpose="Read and return the contents of a remote file",
    category="file_ops",
)
def read_remote_file(input_data: RemoteFileInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
    return executor.run(f"cat {shlex.quote(input_data.file_path)}")


@register_tool(
    name="check_remote_file_exists",
    input_model=RemoteFileInput,
    tags=["ssh", "remote", "file", "check", "primitive"],
    description="Check if a specific file exists on a remote system.",
    safe_mode=True,
    purpose="Determine if a specific file exists on a remote machine",
    category="file_ops",
)
def check_remote_file_exists(input_data: RemoteFileInput) -> str:
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
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
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
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
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
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
    user, host = get_user_host_from_string(input_data.host)
    executor = SSHExecutor(host=host, user=user, ssh_key_path=input_data.ssh_key_path)
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
    logger.info("Diffing two text blocks")
    old_lines = input_data.old.strip().splitlines()
    new_lines = input_data.new.strip().splitlines()
    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile="old", tofile="new", lineterm=""
    )
    return "\n".join(diff)
