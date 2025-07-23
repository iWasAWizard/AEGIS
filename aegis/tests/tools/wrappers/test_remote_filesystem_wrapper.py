# aegis/tests/tools/wrappers/test_remote_filesystem_wrapper.py
"""
Unit tests for the remote filesystem wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.wrapper_filesystem import (
    diff_remote_file_after_edit,
    DiffRemoteFileAfterEditInput,
)


@pytest.fixture
def mock_ssh_executor_instance(monkeypatch):
    """Mocks the SSHExecutor class and its instance methods."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = "default_ssh_run_output"

    mock_executor_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aegis.tools.wrappers.wrapper_filesystem.SSHExecutor", mock_executor_class
    )
    monkeypatch.setattr(
        "aegis.tools.wrappers.wrapper_filesystem.get_machine", MagicMock()
    )
    return mock_instance


def test_diff_remote_file_after_edit_success(mock_ssh_executor_instance):
    original_content = "Version = 1.0"
    new_content = "Version = 2.0"
    mock_ssh_executor_instance.run.side_effect = [original_content, ""]

    input_data = DiffRemoteFileAfterEditInput(
        machine_name="test-host", file_path="/app/config", new_contents=new_content
    )
    result = diff_remote_file_after_edit(input_data)

    assert mock_ssh_executor_instance.run.call_count == 2
    assert "-Version = 1.0" in result
    assert "+Version = 2.0" in result
