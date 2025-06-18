# aegis/tests/tools/primitives/test_filesystem_primitive.py
"""
Unit tests for the filesystem primitive tools.
"""
from unittest.mock import MagicMock, patch

import pytest

from aegis.exceptions import ToolExecutionError  # Ensure this is imported
from aegis.tools.primitives.primitive_filesystem import (
    create_random_file,
    CreateRandomFileInput,
    diff_text_blocks,
    DiffTextBlocksInput,
    transfer_file_to_remote,
    TransferFileToRemoteInput,
    fetch_file_from_remote,
    FetchFileFromRemoteInput,
    read_remote_file,
    MachineFileInput,  # MachineFileInput is used by read_remote_file
    check_remote_file_exists,  # Uses MachineFileInput
    run_remote_script,
    RunRemoteScriptInput,
    append_to_remote_file,
    AppendToRemoteFileInput,
    get_remote_directory_listing,
    GetRemoteDirectoryListingInput,
)
from aegis.tools.primitives.primitive_system import RunLocalCommandInput


@pytest.fixture
def mock_run_local_command_for_dd(monkeypatch):
    """Mocks the run_local_command primitive specifically for create_random_file."""
    mock = MagicMock(return_value="dd command output")
    monkeypatch.setattr(
        "aegis.tools.primitives.primitive_filesystem.run_local_command", mock
    )
    return mock


@pytest.fixture
def mock_ssh_executor_instance(monkeypatch):
    """
    Mocks the SSHExecutor class to return a mock instance,
    and returns the mock instance for further configuration in tests.
    """
    mock_instance = MagicMock()
    # Default behavior for methods, can be overridden in tests
    mock_instance.run.return_value = "mocked ssh run output"
    mock_instance.upload.return_value = "mocked ssh upload success"
    mock_instance.download.return_value = "mocked ssh download success"
    mock_instance.check_file_exists.return_value = True

    mock_ssh_executor_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aegis.tools.primitives.primitive_filesystem.SSHExecutor",
        mock_ssh_executor_class,
    )
    # Also mock get_machine as it's used before SSHExecutor instantiation
    monkeypatch.setattr(
        "aegis.tools.primitives.primitive_filesystem.get_machine", MagicMock()
    )
    return mock_instance


# --- Tests for create_random_file (does not use SSHExecutor) ---
@pytest.mark.parametrize(
    "size_input, expected_dd_command_part_bs, expected_dd_command_part_count",
    [
        ("10k", "bs=1K", "count=10"),
        ("25M", "bs=1K", "count=25600"),
        ("1G", "bs=1K", "count=1048576"),
        ("512", "bs=1K", "count=1"),  # dd will handle small sizes with bs=1K count=1
        ("1023", "bs=1K", "count=1"),
        ("1024", "bs=1K", "count=1"),
        ("0", "bs=1K", "count=0"),
        (
            "500b",
            "bs=1K",
            "count=1",
        ),  # Treat 'b' suffix same as no suffix for this simple parser
        ("700B", "bs=1K", "count=1"),
    ],
)
def test_create_random_file_command_generation(
    mock_run_local_command_for_dd,
    size_input,
    expected_dd_command_part_bs,
    expected_dd_command_part_count,
):
    input_data = CreateRandomFileInput(file_path="test.dat", size=size_input)
    create_random_file(input_data)

    mock_run_local_command_for_dd.assert_called_once()
    call_args = mock_run_local_command_for_dd.call_args[0][0]
    assert isinstance(call_args, RunLocalCommandInput)
    command = call_args.command
    assert "dd if=/dev/urandom of='test.dat'" in command
    assert expected_dd_command_part_bs in command
    assert expected_dd_command_part_count in command


def test_create_random_file_invalid_size(mock_run_local_command_for_dd):
    input_data = CreateRandomFileInput(file_path="test.dat", size="10megabytes")
    result = create_random_file(input_data)
    assert "[ERROR] Invalid size format" in result
    mock_run_local_command_for_dd.assert_not_called()


# --- Tests for diff_text_blocks (does not use SSHExecutor) ---
def test_diff_text_blocks():
    old_text = "hello world\nthis is line 2\ngoodbye"
    new_text = "hello mars\nthis is line 2\nfarewell"

    input_data = DiffTextBlocksInput(old=old_text, new=new_text)
    result = diff_text_blocks(input_data)

    assert "--- old" in result
    assert "+++ new" in result
    assert "@@ -1,3 +1,3 @@" in result
    assert "-hello world" in result
    assert "+hello mars" in result
    assert " this is line 2" in result
    assert "-goodbye" in result
    assert "+farewell" in result


# --- Tests for SSHExecutor-based tools ---


def test_transfer_file_to_remote_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.upload.return_value = (
        "Successfully uploaded /local/src to testhost:/remote/dest"
    )
    input_data = TransferFileToRemoteInput(
        machine_name="testhost",
        source_path="/local/src",
        destination_path="/remote/dest",
    )
    result = transfer_file_to_remote(input_data)
    mock_ssh_executor_instance.upload.assert_called_once_with(
        "/local/src", "/remote/dest"
    )
    assert result == "Successfully uploaded /local/src to testhost:/remote/dest"


def test_transfer_file_to_remote_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.upload.side_effect = ToolExecutionError(
        "SCP upload failed"
    )
    input_data = TransferFileToRemoteInput(
        machine_name="testhost", source_path="/bad/src", destination_path="/remote/dest"
    )
    with pytest.raises(ToolExecutionError, match="SCP upload failed"):
        transfer_file_to_remote(input_data)
    mock_ssh_executor_instance.upload.assert_called_once_with(
        "/bad/src", "/remote/dest"
    )


def test_fetch_file_from_remote_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.download.return_value = (
        "Successfully downloaded testhost:/remote/src to /local/dest"
    )
    input_data = FetchFileFromRemoteInput(
        machine_name="testhost", file_path="/remote/src", local_path="/local/dest"
    )
    result = fetch_file_from_remote(input_data)
    mock_ssh_executor_instance.download.assert_called_once_with(
        "/remote/src", "/local/dest"
    )
    assert result == "Successfully downloaded testhost:/remote/src to /local/dest"


def test_fetch_file_from_remote_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.download.side_effect = ToolExecutionError(
        "SCP download failed"
    )
    input_data = FetchFileFromRemoteInput(
        machine_name="testhost", file_path="/bad/remote", local_path="/local/dest"
    )
    with pytest.raises(ToolExecutionError, match="SCP download failed"):
        fetch_file_from_remote(input_data)
    mock_ssh_executor_instance.download.assert_called_once_with(
        "/bad/remote", "/local/dest"
    )


def test_read_remote_file_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = "remote file content"
    input_data = MachineFileInput(machine_name="testhost", file_path="/path/file.txt")
    result = read_remote_file(input_data)
    mock_ssh_executor_instance.run.assert_called_once_with("cat '/path/file.txt'")
    assert result == "remote file content"


def test_read_remote_file_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError("Remote cat failed")
    input_data = MachineFileInput(
        machine_name="testhost", file_path="/path/badfile.txt"
    )
    with pytest.raises(ToolExecutionError, match="Remote cat failed"):
        read_remote_file(input_data)
    mock_ssh_executor_instance.run.assert_called_once_with("cat '/path/badfile.txt'")


def test_check_remote_file_exists_positive(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = True
    input_data = MachineFileInput(machine_name="testhost", file_path="/path/exists.txt")
    result = check_remote_file_exists(input_data)
    assert result == "Exists"
    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/path/exists.txt"
    )


def test_check_remote_file_exists_negative(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = False
    input_data = MachineFileInput(
        machine_name="testhost", file_path="/path/missing.txt"
    )
    result = check_remote_file_exists(input_data)
    assert result == "Missing"
    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/path/missing.txt"
    )


def test_check_remote_file_exists_executor_error(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.side_effect = ToolExecutionError(
        "SSH connection issue"
    )
    input_data = MachineFileInput(machine_name="testhost", file_path="/path/any.txt")
    with pytest.raises(ToolExecutionError, match="SSH connection issue"):
        check_remote_file_exists(input_data)


def test_run_remote_script_success(mock_ssh_executor_instance):
    # executor.upload returns a success message string
    mock_ssh_executor_instance.upload.return_value = "Upload successful"
    # executor.run returns the script output string
    mock_ssh_executor_instance.run.return_value = "script output here"

    input_data = RunRemoteScriptInput(
        machine_name="testhost", script_path="local.sh", remote_path="/tmp/remote.sh"
    )
    result = run_remote_script(input_data)

    mock_ssh_executor_instance.upload.assert_called_once_with(
        "local.sh", "/tmp/remote.sh"
    )
    mock_ssh_executor_instance.run.assert_called_once_with("bash '/tmp/remote.sh'")
    assert result == "script output here"


def test_run_remote_script_upload_fails(mock_ssh_executor_instance):
    mock_ssh_executor_instance.upload.side_effect = ToolExecutionError(
        "SCP upload permission denied"
    )
    input_data = RunRemoteScriptInput(
        machine_name="testhost", script_path="local.sh", remote_path="/tmp/remote.sh"
    )
    with pytest.raises(ToolExecutionError, match="SCP upload permission denied"):
        run_remote_script(input_data)
    mock_ssh_executor_instance.run.assert_not_called()  # Script execution should not be attempted


def test_run_remote_script_execution_fails(mock_ssh_executor_instance):
    mock_ssh_executor_instance.upload.return_value = "Upload successful"
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Remote script execution error"
    )
    input_data = RunRemoteScriptInput(
        machine_name="testhost", script_path="local.sh", remote_path="/tmp/remote.sh"
    )
    with pytest.raises(ToolExecutionError, match="Remote script execution error"):
        run_remote_script(input_data)
    mock_ssh_executor_instance.upload.assert_called_once()  # Upload was attempted
    mock_ssh_executor_instance.run.assert_called_once_with("bash '/tmp/remote.sh'")


def test_append_to_remote_file_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = ""  # tee is often silent
    input_data = AppendToRemoteFileInput(
        machine_name="testhost", file_path="/app/config.log", content="new log line"
    )
    result = append_to_remote_file(input_data)

    expected_cmd = "echo 'new log line' | sudo tee -a '/app/config.log'"
    mock_ssh_executor_instance.run.assert_called_once_with(expected_cmd)
    assert result == ""  # Directly returns output of executor.run


def test_append_to_remote_file_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Remote tee command failed"
    )
    input_data = AppendToRemoteFileInput(
        machine_name="testhost", file_path="/app/config.log", content="new log line"
    )
    with pytest.raises(ToolExecutionError, match="Remote tee command failed"):
        append_to_remote_file(input_data)


def test_get_remote_directory_listing_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = (
        "drwxr-xr-x  2 user group 4096 Jan  1 12:00 mydir"
    )
    input_data = GetRemoteDirectoryListingInput(
        machine_name="testhost", directory_path="/home/user"
    )
    result = get_remote_directory_listing(input_data)

    mock_ssh_executor_instance.run.assert_called_once_with("ls -la '/home/user'")
    assert result == "drwxr-xr-x  2 user group 4096 Jan  1 12:00 mydir"


def test_get_remote_directory_listing_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError("Remote ls failed")
    input_data = GetRemoteDirectoryListingInput(
        machine_name="testhost", directory_path="/nonexistent"
    )
    with pytest.raises(ToolExecutionError, match="Remote ls failed"):
        get_remote_directory_listing(input_data)
