# aegis/tests/tools/primitives/test_filesystem_primitive.py
"""
Unit tests for the filesystem primitive tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.primitives.primitive_filesystem import (
    transfer_file_to_remote,
    TransferFileToRemoteInput,
    fetch_file_from_remote,
    FetchFileFromRemoteInput,
    read_remote_file,
    MachineFileInput,
    check_remote_file_exists,
    run_remote_script,
    RunRemoteScriptInput,
    append_to_remote_file,
    AppendToRemoteFileInput,
    get_remote_directory_listing,
    GetRemoteDirectoryListingInput,
)


@pytest.fixture
def mock_ssh_executor_instance(monkeypatch):
    """Mocks the SSHExecutor class and its instance methods."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = "mocked ssh run output"
    mock_instance.upload.return_value = "mocked ssh upload success"
    mock_instance.download.return_value = "mocked ssh download success"
    mock_instance.check_file_exists.return_value = True

    mock_ssh_executor_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aegis.tools.primitives.primitive_filesystem.SSHExecutor",
        mock_ssh_executor_class,
    )
    monkeypatch.setattr(
        "aegis.tools.primitives.primitive_filesystem.get_machine", MagicMock()
    )
    return mock_instance


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
