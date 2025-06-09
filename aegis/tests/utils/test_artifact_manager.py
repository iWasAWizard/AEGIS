# aegis/tests/utils/test_artifact_manager.py
"""
Unit tests for the artifact management utility.
"""
import re
from pathlib import Path

import pytest

from aegis.utils import artifact_manager


@pytest.fixture
def mock_artifact_dir(tmp_path: Path, monkeypatch):
    """Creates a temporary artifacts directory for testing."""
    artifact_dir = tmp_path / "test_artifacts"
    artifact_dir.mkdir()
    monkeypatch.setattr(artifact_manager, "ARTIFACT_DIR", artifact_dir)
    return artifact_dir


def test_save_artifact_success(mock_artifact_dir: Path, tmp_path: Path):
    """Verify that save_artifact correctly copies and renames the file."""
    # Create a source file to be saved as an artifact
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "result.txt"
    source_file.write_text("This is an artifact.")

    task_id = "test-task-123"
    tool_name = "test_tool"

    dest_path = artifact_manager.save_artifact(source_file, task_id, tool_name)

    # Check that the destination file exists
    assert dest_path.is_file()

    # Check that it's in the correct directory
    assert dest_path.parent == mock_artifact_dir

    # Check the naming convention using a regex
    # Format: {task_id}_{tool}_{timestamp}{suffix}
    # e.g., test-task-123_test_tool_20240101-120000.txt
    pattern = re.compile(rf"^{task_id}_{tool_name}_\d{{8}}-\d{{6}}\.txt$")
    assert pattern.match(dest_path.name)

    # Check that the content is identical
    assert dest_path.read_text() == "This is an artifact."


def test_save_artifact_file_not_found():
    """Verify that a FileNotFoundError is raised if the source file doesn't exist."""
    non_existent_file = Path("/tmp/this/file/does/not/exist.txt")

    with pytest.raises(FileNotFoundError):
        artifact_manager.save_artifact(non_existent_file, "test-task", "test-tool")
