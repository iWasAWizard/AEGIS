# aegis/tests/tools/wrappers/test_filesystem_wrapper.py
"""
Unit tests for the high-level filesystem wrapper tools.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.wrapper_filesystem import (
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
