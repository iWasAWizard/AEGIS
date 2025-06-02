"""
Primitive tools for interacting with the local filesystem.

Includes operations like checking file existence, reading files, listing directories,
and other simple I/O utilities.
"""

import subprocess
from typing import Optional

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class TransferFileToRemoteInput(BaseModel):
    """
    Represents the TransferFileToRemoteInput class.

    Specifies the parameters required to copy a file to a remote location using SSH or SCP.
    """

    source_path: str = Field(description="Path to the local file to transfer.")
    destination_path: str = Field(description="Destination path on the remote machine.")
    host: str = Field(description="Remote host to send the file to (user@host).")
    ssh_key_path: Optional[str] = Field(
        None, description="Path to the SSH private key for authentication."
    )


class FetchFileFromRemoteInput(BaseModel):
    """
    Represents the FetchFileFromRemoteInput class.

    Defines input parameters for retrieving a remote file from a server.
    """

    remote_path: str = Field(description="Path to the file on the remote machine.")
    local_path: str = Field(description="Destination path on the local machine.")
    host: str = Field(description="Remote host (user@host).")
    ssh_key_path: Optional[str] = Field(
        None, description="Path to SSH private key for authentication."
    )


class ReadRemoteFileInput(BaseModel):
    """
    Represents the ReadRemoteFileInput class.

    Used to specify the file path and remote connection details when reading the contents of a file over SSH.
    """

    host: str = Field(description="Remote host (user@host).")
    file_path: str = Field(description="Path to the file on the remote system.")
    ssh_key_path: Optional[str] = Field(
        None, description="Path to the SSH private key."
    )


class CheckRemoteFileExistsInput(BaseModel):
    """
    CheckRemoteFileExistsInput class.
    """

    host: str = Field(description="Remote host (user@host).")
    file_path: str = Field(description="Absolute path to the file to check.")
    ssh_key_path: Optional[str] = Field(
        None, description="Path to the SSH private key."
    )


class RunRemoteScriptInput(BaseModel):
    """
    RunRemoteScriptInput class.
    """

    script_path: str = Field(
        description="Local path to the shell script to send and execute."
    )
    remote_path: str = Field(description="Destination path on the remote machine.")
    host: str = Field(description="Remote host (user@host).")
    ssh_key_path: Optional[str] = Field(
        None, description="Path to SSH private key for authentication."
    )


class AppendToRemoteFileInput(BaseModel):
    """
    AppendToRemoteFileInput class.
    """

    host: str = Field(description="Remote host (user@host).")
    file_path: str = Field(description="Remote file to append to.")
    content: str = Field(description="Text to append to the file.")
    ssh_key_path: Optional[str] = Field(description="Path to SSH private key.")


class GetRemoteDirectoryListingInput(BaseModel):
    """
    GetRemoteDirectoryListingInput class
    """

    host: str = Field(description="Remote host (user@host).")
    directory_path: str = Field(description="Directory path to list.")
    ssh_key_path: Optional[str] = Field(description="Path to SSH private key.")


class DiffTextBlocksInput(BaseModel):
    """
    DiffTextBlocksInput class
    """

    old: str = Field(description="Original block of text.")
    new: str = Field(description="New block of text.")


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
    """
    transfer_file_to_remote
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Transferring file to remote host",
        extra={"event_type": "transfer_file_to_remote", "data": input_data.dict()},
    )
    try:
        scp_cmd = ["scp"]
        if input_data.ssh_key_path:
            scp_cmd += ["-i", input_data.ssh_key_path]
        scp_cmd += [
            input_data.source_path,
            f"{input_data.host}:{input_data.destination_path}",
        ]
        result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[primitive_filesystem] Error: {e}")
        return f"[ERROR] File transfer failed: {str(e)}"


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
    """
    fetch_file_from_remote
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Fetching file from remote host",
        extra={"event_type": "fetch_file_from_remote", "data": input_data.dict()},
    )
    try:
        scp_cmd = ["scp"]
        if input_data.ssh_key_path:
            scp_cmd += ["-i", input_data.ssh_key_path]
        scp_cmd += [
            f"{input_data.host}:{input_data.remote_path}",
            input_data.local_path,
        ]
        result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[primitive_filesystem] Error: {e}")
        return f"[ERROR] SCP fetch failed: {str(e)}"


@register_tool(
    name="read_remote_file",
    input_model=ReadRemoteFileInput,
    tags=["ssh", "remote", "file", "read", "primitive"],
    description="Read the contents of a file on a remote system.",
    safe_mode=True,
    purpose="Read and return the contents of a remote file",
    category="file_ops",
)
def read_remote_file(input_data: ReadRemoteFileInput) -> str:
    """
    read_remote_file
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Reading file from remote system",
        extra={"event_type": "read_remote_file", "data": input_data.dict()},
    )
    try:
        ssh_cmd = ["ssh"]
        if input_data.ssh_key_path:
            ssh_cmd += ["-i", input_data.ssh_key_path]
        ssh_cmd += [input_data.host, f"cat {input_data.file_path}"]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[primitive_filesystem] Error: {e}")
        return f"[ERROR] SSH read failed: {str(e)}"


@register_tool(
    name="check_remote_file_exists",
    input_model=CheckRemoteFileExistsInput,
    tags=["ssh", "remote", "file", "check", "primitive"],
    description="Check if a specific file exists on a remote system.",
    safe_mode=True,
    purpose="Determine if a specific file exists on a remote machine",
    category="file_ops",
)
def check_remote_file_exists(input_data: CheckRemoteFileExistsInput) -> str:
    """
    check_remote_file_exists
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Checking file existence on remote host",
        extra={"event_type": "check_remote_file_exists", "data": input_data.dict()},
    )
    try:
        ssh_cmd = ["ssh"]
        if input_data.ssh_key_path:
            ssh_cmd += ["-i", input_data.ssh_key_path]
        ssh_cmd += [
            input_data.host,
            f"test -f {input_data.file_path} && echo 'Exists' || echo 'Missing'",
        ]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=20)
        return result.stdout.strip()
    except Exception as e:
        logger.exception(f"[primitive_filesystem] Error: {e}")
        return f"[ERROR] File existence check failed: {str(e)}"


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
    """
    run_remote_script
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Uploading and executing remote script",
        extra={"event_type": "run_remote_script", "data": input_data.dict()},
    )
    try:
        scp_cmd = ["scp"]
        if input_data.ssh_key_path:
            scp_cmd += ["-i", input_data.ssh_key_path]
        scp_cmd += [
            input_data.script_path,
            f"{input_data.host}:{input_data.remote_path}",
        ]
        transfer = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
        if transfer.returncode != 0:
            return f"[ERROR] Script upload failed: {transfer.stderr.strip()}"

        ssh_cmd = ["ssh"]
        if input_data.ssh_key_path:
            ssh_cmd += ["-i", input_data.ssh_key_path]
        ssh_cmd += [input_data.host, f"bash {input_data.remote_path}"]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[primitive_filesystem] Error: {e}")
        return f"[ERROR] Remote script execution failed: {str(e)}"


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
    """
    append_to_remote_file
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Appending to remote file",
        extra={"event_type": "append_to_remote_file", "data": input_data.dict()},
    )
    try:
        safe_content = input_data.content.replace('"', '\\"')
        ssh_cmd = ["ssh"]
        if input_data.ssh_key_path:
            ssh_cmd += ["-i", input_data.ssh_key_path]
        ssh_cmd += [
            input_data.host,
            f'echo "{safe_content}" | sudo tee -a {input_data.file_path}',
        ]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[primitive_filesystem] Error: {e}")
        return f"[ERROR] Failed to append to file: {str(e)}"


@register_tool(
    name="get_remote_directory_listing",
    input_model=GetRemoteDirectoryListingInput,
    tags=["ssh", "remote", "directory", "list", "primitive"],
    description="List contents of a directory on a remote machine.",
    safe_mode=True,
    purpose="List the contents of a remote directory using 'ls'",
    category="file_ops",
)
def get_remote_directory_listing(input_data: GetRemoteDirectoryListingInput) -> str:
    """
    get_remote_directory_listing
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Listing remote directory",
        extra={"event_type": "get_remote_directory_listing", "data": input_data.dict()},
    )
    try:
        ssh_cmd = ["ssh"]
        if input_data.ssh_key_path:
            ssh_cmd += ["-i", input_data.ssh_key_path]
        ssh_cmd += [input_data.host, f"ls -lah {input_data.directory_path}"]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[primitive_filesystem] Error: {e}")
        return f"[ERROR] Directory listing failed: {str(e)}"


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
    """
    diff_text_blocks
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    import difflib

    logger.info(
        "Diffing two text blocks", extra={"event_type": "diff_text_blocks", "data": {}}
    )
    old_lines = input_data.old.strip().splitlines()
    new_lines = input_data.new.strip().splitlines()
    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile="old", tofile="new", lineterm=""
    )
    return "\n".join(diff)
