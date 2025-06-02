"""Handles task artifact file operations, including structured renaming and logging.

Includes logic to organize and timestamp output files for reproducibility and analysis."""

import shutil
from datetime import datetime
from pathlib import Path

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)


def save_artifact(file_path: Path, task_id: str, tool: str) -> Path:
    """
    Standardizes and copies a file into the artifact directory.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} not found")
    logger.error("Error raised during utility operation")

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    new_name = f"{task_id}_{tool}_{timestamp}{file_path.suffix}"
    dest_path = ARTIFACT_DIR / new_name
    shutil.copy(file_path, dest_path)
    return dest_path
