# aegis/utils/artifact_manager.py
"""Handles task artifact file operations, including structured renaming and logging.

This utility provides a centralized function for saving files generated during a
task's execution (e.g., screenshots, downloaded logs, reports) into a structured
`artifacts/` directory. It ensures that all saved files are uniquely named and
associated with the task and tool that created them.
"""

import shutil
from datetime import datetime
from pathlib import Path

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)


def save_artifact(file_path: Path, task_id: str, tool: str) -> Path:
    """Copies a file to the artifact directory with a standardized, timestamped name.

    The new filename follows the format:
    `{task_id}_{tool}_{timestamp}{original_extension}`
    Example: `task-abc-123_capture_screenshot_20230101-120000.png`

    :param file_path: The path to the source file to be saved.
    :type file_path: Path
    :param task_id: The ID of the task that generated the artifact.
    :type task_id: str
    :param tool: The name of the tool that generated the artifact.
    :type tool: str
    :return: The destination path of the newly saved artifact.
    :rtype: Path
    :raises FileNotFoundError: If the source file does not exist.
    :raises IOError: If the file copy operation fails.
    """
    if not file_path.exists():
        logger.error(f"Attempted to save non-existent artifact from path: {file_path}")
        raise FileNotFoundError(f"Source artifact file not found: {file_path}")

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    new_name = f"{task_id}_{tool}_{timestamp}{file_path.suffix}"
    dest_path = ARTIFACT_DIR / new_name

    try:
        shutil.copy(file_path, dest_path)
        logger.info(f"Saved artifact '{file_path.name}' to '{dest_path}'")
        return dest_path
    except Exception as e:
        logger.exception(f"Failed to copy artifact from '{file_path}' to '{dest_path}'")
        raise IOError(f"Could not save artifact: {e}") from e
