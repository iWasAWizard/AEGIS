# aegis/tests/tools/wrappers/test_filesystem_wrapper.py
"""
Unit tests for the high-level filesystem wrapper tools.
"""
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.wrapper_filesystem import (
    retrieve_remote_log_file,
    RetrieveRemoteLogFileInput,
    check_and_read_config_file,
    MachineFileInput,
    backup_remote_file,
    BackupRemoteFileInput,
    inject_line_into_config,
    InjectLineIntoConfigInput,
    diff_remote_file_after_edit,
    DiffRemoteFileAfterEditInput,
    diff_local_file_after_edit,
    DiffLocalFileAfterEditInput,
)


@pytest.fixture
def mock_ssh_executor_instance(monkeypatch):
    """
    Mocks the SSHExecutor class to return a mock instance,
    and returns the mock instance for further configuration in tests.
    """
    mock_instance = MagicMock()
    # Set up default behaviors that can be overridden in individual tests
    mock_instance.run.return_value = "default_ssh_run_output"
    mock_instance.upload.return_value = "default_ssh_upload_success_message"
    mock_instance.download.return_value = "default_ssh_download_success_message"
    mock_instance.check_file_exists.return_value = True  # Default to file existing

    mock_ssh_executor_class = MagicMock(return_value=mock_instance)
    # Patch where SSHExecutor is imported in the module under test
    monkeypatch.setattr(
        "aegis.tools.wrappers.wrapper_filesystem.SSHExecutor", mock_ssh_executor_class
    )
    monkeypatch.setattr(
        "aegis.tools.wrappers.wrapper_filesystem.get_machine", MagicMock()
    )
    return mock_instance


# --- Tests ---


def test_retrieve_remote_log_file_success(mock_ssh_executor_instance):
    expected_msg = "Successfully downloaded remote/server.log to local/server.log_today"
    mock_ssh_executor_instance.download.return_value = expected_msg

    input_data = RetrieveRemoteLogFileInput(
        machine_name="test-host",
        file_path="remote/server.log",
        local_destination="local/server.log_today",
    )
    result = retrieve_remote_log_file(input_data)

    mock_ssh_executor_instance.download.assert_called_once_with(
        remote_path="remote/server.log", local_path="local/server.log_today"
    )
    assert result == expected_msg


def test_retrieve_remote_log_file_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.download.side_effect = ToolExecutionError(
        "SCP download failed miserably"
    )
    input_data = RetrieveRemoteLogFileInput(
        machine_name="test-host",
        file_path="remote/server.log",
        local_destination="local/server.log_today",
    )
    with pytest.raises(ToolExecutionError, match="SCP download failed miserably"):
        retrieve_remote_log_file(input_data)
    mock_ssh_executor_instance.download.assert_called_once_with(
        remote_path="remote/server.log", local_path="local/server.log_today"
    )


def test_check_and_read_config_file_exists_and_readable(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = True
    mock_ssh_executor_instance.run.return_value = "config_content_here"

    input_data = MachineFileInput(
        machine_name="test-host", file_path="/etc/myconfig.conf"
    )
    result = check_and_read_config_file(input_data)

    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/etc/myconfig.conf"
    )
    mock_ssh_executor_instance.run.assert_called_once_with("cat '/etc/myconfig.conf'")
    assert result == "config_content_here"


def test_check_and_read_config_file_missing(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = False

    input_data = MachineFileInput(
        machine_name="test-host", file_path="/etc/nonexistent.conf"
    )
    result = check_and_read_config_file(input_data)

    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/etc/nonexistent.conf"
    )
    mock_ssh_executor_instance.run.assert_not_called()
    assert (
        "[INFO] File does not exist at '/etc/nonexistent.conf', so it cannot be read."
        in result
    )


def test_check_and_read_config_file_exists_but_read_fails(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = True
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Permission denied reading remote file"
    )

    input_data = MachineFileInput(
        machine_name="test-host", file_path="/etc/protected.conf"
    )
    with pytest.raises(
        ToolExecutionError, match="Permission denied reading remote file"
    ):
        check_and_read_config_file(input_data)
    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/etc/protected.conf"
    )
    mock_ssh_executor_instance.run.assert_called_once_with("cat '/etc/protected.conf'")


def test_backup_remote_file_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = True
    # executor.run for 'cp' is often silent on success, our tool returns custom message
    mock_ssh_executor_instance.run.return_value = ""

    input_data = BackupRemoteFileInput(
        machine_name="test-host", file_path="/data/important.doc"
    )
    result = backup_remote_file(input_data)

    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/data/important.doc"
    )
    mock_ssh_executor_instance.run.assert_called_once_with(
        "sudo cp '/data/important.doc' '/data/important.doc.bak'"
    )
    assert result == "Successfully created backup: /data/important.doc.bak"


def test_backup_remote_file_source_missing(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = False
    input_data = BackupRemoteFileInput(
        machine_name="test-host", file_path="/data/absent.doc"
    )
    result = backup_remote_file(input_data)

    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/data/absent.doc"
    )
    mock_ssh_executor_instance.run.assert_not_called()
    assert "[INFO] File '/data/absent.doc' does not exist. Skipping backup." in result


def test_backup_remote_file_cp_command_fails(mock_ssh_executor_instance):
    mock_ssh_executor_instance.check_file_exists.return_value = True
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Remote cp command failed due to disk full"
    )

    input_data = BackupRemoteFileInput(
        machine_name="test-host", file_path="/data/important.doc"
    )
    with pytest.raises(
        ToolExecutionError, match="Remote cp command failed due to disk full"
    ):
        backup_remote_file(input_data)
    mock_ssh_executor_instance.check_file_exists.assert_called_once_with(
        "/data/important.doc"
    )
    mock_ssh_executor_instance.run.assert_called_once_with(
        "sudo cp '/data/important.doc' '/data/important.doc.bak'"
    )


def test_inject_line_into_config_success(mock_ssh_executor_instance):
    # executor.run for 'echo | sudo tee' is often silent on success, tool returns custom message
    mock_ssh_executor_instance.run.return_value = ""
    input_data = InjectLineIntoConfigInput(
        machine_name="test-host",
        file_path="/opt/app/settings.ini",
        line="new_setting=true",
    )
    result = inject_line_into_config(input_data)

    expected_cmd = "echo 'new_setting=true' | sudo tee -a '/opt/app/settings.ini'"
    mock_ssh_executor_instance.run.assert_called_once_with(expected_cmd)
    assert result == "Successfully injected line into /opt/app/settings.ini"


def test_inject_line_into_config_tee_command_fails(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Remote tee command failed, no write permission"
    )
    input_data = InjectLineIntoConfigInput(
        machine_name="test-host",
        file_path="/opt/app/settings.ini",
        line="new_setting=true",
    )
    with pytest.raises(
        ToolExecutionError, match="Remote tee command failed, no write permission"
    ):
        inject_line_into_config(input_data)
    expected_cmd = "echo 'new_setting=true' | sudo tee -a '/opt/app/settings.ini'"
    mock_ssh_executor_instance.run.assert_called_once_with(expected_cmd)


def test_diff_remote_file_after_edit_success(mock_ssh_executor_instance):
    original_content = "Version = 1.0\nAuthor = AEGIS"
    new_content = "Version = 2.0\nAuthor = AEGIS\nReviewed = true"

    # Configure side_effect for multiple calls to executor.run
    # First call (cat original): returns original_content
    # Second call (tee new content): returns "" (silent success)
    mock_ssh_executor_instance.run.side_effect = [original_content, ""]

    input_data = DiffRemoteFileAfterEditInput(
        machine_name="test-host", file_path="/srv/app/VERSION", new_contents=new_content
    )
    result = diff_remote_file_after_edit(input_data)

    assert mock_ssh_executor_instance.run.call_count == 2
    calls = mock_ssh_executor_instance.run.call_args_list
    assert calls[0][0][0] == "cat '/srv/app/VERSION'"  # Args of first call
    assert (
        calls[1][0][0]
        == f"echo '{new_content}' | sudo tee '/srv/app/VERSION' > /dev/null"
    )  # Args of second call

    assert "--- /srv/app/VERSION (before)" in result
    assert "+++ /srv/app/VERSION (after)" in result
    assert "-Version = 1.0" in result
    assert "+Version = 2.0" in result
    assert " Author = AEGIS" in result
    assert "+Reviewed = true" in result


def test_diff_remote_file_after_edit_read_original_fails(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Failed to cat original_contents"
    )
    input_data = DiffRemoteFileAfterEditInput(
        machine_name="test-host", file_path="/srv/app/VERSION", new_contents="anything"
    )
    with pytest.raises(ToolExecutionError, match="Failed to cat original_contents"):
        diff_remote_file_after_edit(input_data)
    mock_ssh_executor_instance.run.assert_called_once_with("cat '/srv/app/VERSION'")


def test_diff_remote_file_after_edit_write_new_fails(mock_ssh_executor_instance):
    original_content = "Version = 1.0"
    new_content = "Version = 2.0"
    mock_ssh_executor_instance.run.side_effect = [
        original_content,  # cat succeeds
        ToolExecutionError("Failed to tee new_contents"),  # tee fails
    ]
    input_data = DiffRemoteFileAfterEditInput(
        machine_name="test-host", file_path="/srv/app/VERSION", new_contents=new_content
    )
    with pytest.raises(ToolExecutionError, match="Failed to tee new_contents"):
        diff_remote_file_after_edit(input_data)
    assert mock_ssh_executor_instance.run.call_count == 2


# Tests for diff_local_file_after_edit (no SSHExecutor involvement)
def test_diff_local_file_after_edit_success(tmp_path: Path):
    local_file = tmp_path / "local_diff_test.txt"
    original_text = "alpha\nbeta\ngamma"
    local_file.write_text(original_text)

    new_text = "alpha\ndelta\ngamma"
    input_data = DiffLocalFileAfterEditInput(
        file_path=str(local_file), replacement_text=new_text
    )
    result = diff_local_file_after_edit(input_data)

    assert local_file.read_text() == new_text
    assert "-beta" in result
    assert "+delta" in result


def test_diff_local_file_after_edit_file_not_found():
    input_data = DiffLocalFileAfterEditInput(
        file_path="non_existent_local_for_diff.txt", replacement_text="text"
    )
    with pytest.raises(
        ToolExecutionError,
        match="Local file not found: non_existent_local_for_diff.txt",
    ):
        diff_local_file_after_edit(input_data)
