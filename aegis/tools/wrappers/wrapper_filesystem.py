"""
Filesystem wrapper tools for higher-level file operations.

Extends primitives to support workflows like file search, batch reads, uploads, and more.
May include integrations with remote storage or validation logic.
"""

from typing import Optional

from pydantic import BaseModel

from aegis.registry import register_tool
from aegis.tools.primitives import (
    fetch_file_from_remote,
    check_remote_file_exists,
    read_remote_file,
    ReadRemoteFileInput,
    append_to_remote_file,
    AppendToRemoteFileInput,
    get_remote_directory_listing,
    GetRemoteDirectoryListingInput,
    diff_text_blocks,
    DiffTextBlocksInput,
    FetchFileFromRemoteInput,
    CheckRemoteFileExistsInput,
)
from aegis.tools.wrappers.shell import run_remote_command, RunRemoteCommandInput
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class RetrieveRemoteLogFileInput(BaseModel):
    """
    RetrieveRemoteLogFileInput class.
    """

    host: str
    remote_log_path: str
    local_destination: str
    ssh_key_path: str


class CheckAndReadConfigFileInput(BaseModel):
    """
    CheckAndReadConfigFileInput class.
    """

    host: str
    config_path: str
    ssh_key_path: str


class BackupRemoteFileInput(BaseModel):
    """
    BackupRemoteFileInput class.
    """

    host: str
    file_path: str
    ssh_key_path: str


class InjectLineIntoConfigInput(BaseModel):
    """
    InjectLineIntoConfigInput class.
    """

    host: str
    file_path: str
    line: str
    ssh_key_path: str


class ListRemoteLogDirectoryInput(BaseModel):
    """
    ListRemoteLogDirectoryInput class.
    """

    host: str
    ssh_key_path: str


class ClearRemoteTempInput(BaseModel):
    """
    ClearRemoteTempInput class.
    """

    host: str
    ssh_key_path: str


class DiffLocalFileAfterEditInput(BaseModel):
    """
    DiffLocalFileAfterEditInput class.
    """

    file_path: str
    replacement_text: str


class DiffRemoteFileAfterEditInput(BaseModel):
    """
    DiffRemoteFileAfterEditInput class.
    """

    host: str
    file_path: str
    new_contents: str
    ssh_key_path: Optional[str]


@register_tool(
    name="retrieve_remote_log_file",
    input_model=RetrieveRemoteLogFileInput,
    tags=["ssh", "scp", "log", "midlevel"],
    description="Download a log file from a remote system.",
    safe_mode=True,
    purpose="Download a log file from a remote machine",
    category="file_ops",
)
def retrieve_remote_log_file(input_data: RetrieveRemoteLogFileInput) -> str:
    """
    retrieve_remote_log_file.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Retrieving remote log file",
        event_type="retrieve_remote_log_file",
        data=input_data.dict(),
    )
    return fetch_file_from_remote(
        FetchFileFromRemoteInput(
            remote_path=input_data.remote_log_path,
            local_path=input_data.local_destination,
            host=input_data.host,
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="check_and_read_config_file",
    input_model=CheckAndReadConfigFileInput,
    tags=["ssh", "file", "config", "midlevel"],
    description="Read a remote config file only if it exists.",
    safe_mode=True,
    purpose="Check if a remote config file exists and print its contents",
    category="file_ops",
)
def check_and_read_config_file(input_data: CheckAndReadConfigFileInput) -> str:
    """
    check_and_read_config_file.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Verifying configuration file",
        event_type="check_and_read_config_file",
        data=input_data.dict(),
    )
    exists = check_remote_file_exists(
        CheckRemoteFileExistsInput(
            host=input_data.host,
            file_path=input_data.config_path,
            ssh_key_path=input_data.ssh_key_path,
        )
    )
    if "Exists" in exists:
        return read_remote_file(
            ReadRemoteFileInput(
                host=input_data.host,
                file_path=input_data.config_path,
                ssh_key_path=input_data.ssh_key_path,
            )
        )
    else:
        return f"[INFO] Config file does not exist: {input_data.config_path}"


@register_tool(
    name="backup_remote_file",
    tags=["scp"],
    input_model=BackupRemoteFileInput,
    description="Copy a file to a .bak version if it exists.",
    safe_mode=True,
    purpose="Create a .bak backup of a remote file if it exists",
    category="file_ops",
)
def backup_remote_file(input_data: BackupRemoteFileInput) -> str:
    """
    backup_remote_file.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Backing up remote file",
        event_type="backup_remote_file",
        data=input_data.dict(),
    )
    exists = check_remote_file_exists(
        CheckRemoteFileExistsInput(
            host=input_data.host,
            file_path=input_data.file_path,
            ssh_key_path=input_data.ssh_key_path,
        )
    )
    if "Exists" not in exists:
        return f"[INFO] File {input_data.file_path} does not exist. Skipping backup."
    cmd = f"cp {input_data.file_path} {input_data.file_path}.bak"
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command=f"sudo {cmd}",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="inject_line_into_config",
    input_model=InjectLineIntoConfigInput,
    tags=["ssh", "config", "append", "midlevel"],
    description="Appends a line to a remote config file.",
    safe_mode=True,
    purpose="Append a line of configuration to a remote file",
    category="file_ops",
)
def inject_line_into_config(input_data: InjectLineIntoConfigInput) -> str:
    """
    inject_line_into_config.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Injecting line into remote config",
        event_type="inject_line_into_config",
        data=input_data.dict(),
    )
    return append_to_remote_file(
        AppendToRemoteFileInput(
            host=input_data.host,
            file_path=input_data.file_path,
            content=input_data.line,
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="list_remote_log_directory",
    input_model=ListRemoteLogDirectoryInput,
    tags=["ssh", "remote", "logs", "midlevel"],
    description="List contents of /var/log/ on the remote host.",
    safe_mode=True,
    purpose="List all files inside /var/log on a remote system",
    category="file_ops",
)
def list_remote_log_directory(input_data: ListRemoteLogDirectoryInput) -> str:
    """
    list_remote_log_directory.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Listing remote log directory",
        event_type="list_remote_log_directory",
        data=input_data.dict(),
    )
    return get_remote_directory_listing(
        GetRemoteDirectoryListingInput(
            host=input_data.host,
            directory_path="/var/log",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="clear_remote_temp",
    input_model=ClearRemoteTempInput,
    tags=["ssh", "remote", "cleanup", "midlevel"],
    description="Clear /tmp and /var/tmp on a remote system.",
    safe_mode=True,
    purpose="Delete all temporary files from /tmp and /var/tmp remotely",
    category="system",
)
def clear_remote_temp(input_data: ClearRemoteTempInput) -> str:
    """
    clear_remote_temp.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Clearing remote temp directories",
        event_type="clear_remote_temp",
        data=input_data.dict(),
    )
    return run_remote_command(
        RunRemoteCommandInput(
            host=input_data.host,
            command="sudo rm -rf /tmp/* /var/tmp/*",
            ssh_key_path=input_data.ssh_key_path,
        )
    )


@register_tool(
    name="diff_local_file_after_edit",
    input_model=DiffLocalFileAfterEditInput,
    tags=["local", "file", "edit", "diff", "midlevel"],
    description="Capture original contents of a local file, modify it, and return a diff.",
    safe_mode=True,
    purpose="Compare local file contents before and after a replacement",
    category="file_ops",
)
def diff_local_file_after_edit(input_data: DiffLocalFileAfterEditInput) -> str:
    """
    diff_local_file_after_edit.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Diffing local file after edit",
        event_type="diff_local_file_after_edit",
        data=input_data.dict(),
    )
    try:
        with open(input_data.file_path, "r") as f:
            old = f.read()
        with open(input_data.file_path, "w") as f:
            f.write(input_data.replacement_text)
        return diff_text_blocks(
            DiffTextBlocksInput(old=old, new=input_data.replacement_text)
        )
    except Exception as e:
        return f"[ERROR] Failed to edit and diff local file: {str(e)}"


@register_tool(
    name="diff_remote_file_after_edit",
    input_model=DiffRemoteFileAfterEditInput,
    tags=["remote", "file", "edit", "diff", "midlevel"],
    description="Read and diff a remote file before and after replacing its contents.",
    safe_mode=True,
    purpose="Compare remote file contents before and after a replacement",
    category="file_ops",
)
def diff_remote_file_after_edit(input_data: DiffRemoteFileAfterEditInput) -> str:
    """
    diff_remote_file_after_edit.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        "Diffing remote file after edit",
        event_type="diff_remote_file_after_edit",
        data=input_data.dict(),
    )
    try:
        old_contents = read_remote_file(
            ReadRemoteFileInput(
                host=input_data.host,
                file_path=input_data.file_path,
                ssh_key_path=input_data.ssh_key_path,
            )
        )
        safe_text = input_data.new_contents.replace('"', '\\"').replace("`", "\\`")
        echo_cmd = f'echo "{safe_text}" | sudo tee {input_data.file_path}'
        run_remote_command(
            RunRemoteCommandInput(
                host=input_data.host,
                command=echo_cmd,
                ssh_key_path=input_data.ssh_key_path,
            )
        )
        return diff_text_blocks(
            DiffTextBlocksInput(old=old_contents, new=input_data.new_contents)
        )
    except Exception as e:
        return f"[ERROR] Failed to edit and diff remote file: {str(e)}"
