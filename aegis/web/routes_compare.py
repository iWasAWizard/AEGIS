# aegis/web/routes_compare.py
"""
API route for comparing artifacts from two different task runs.
"""

import difflib
from pathlib import Path

from fastapi import APIRouter, HTTPException

from aegis.utils.logger import setup_logger

router = APIRouter()
REPORTS_DIR = Path("reports")
logger = setup_logger(__name__)


@router.get("/compare", tags=["Artifacts"])
async def compare_artifacts(task1_id: str, task2_id: str) -> dict:
    """Compares the summary.md files of two tasks and returns a diff.

    :param task1_id: The ID of the first task.
    :type task1_id: str
    :param task2_id: The ID of the second task.
    :type task2_id: str
    :return: A dictionary containing the two task IDs and the unified diff.
    :rtype: dict
    :raises HTTPException: If one or both summary files are not found.
    """
    logger.info(f"Compare request received for tasks: {task1_id} vs {task2_id}")

    summary1_path = REPORTS_DIR / task1_id / "summary.md"
    summary2_path = REPORTS_DIR / task2_id / "summary.md"

    if not summary1_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"Summary for task '{task1_id}' not found."
        )
    if not summary2_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"Summary for task '{task2_id}' not found."
        )

    try:
        lines1 = summary1_path.read_text(encoding="utf-8").splitlines()
        lines2 = summary2_path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        logger.exception("Failed to read summary files for comparison.")
        raise HTTPException(status_code=500, detail=f"Error reading summary files: {e}")

    diff_generator = difflib.unified_diff(
        lines1,
        lines2,
        fromfile=f"{task1_id}/summary.md",
        tofile=f"{task2_id}/summary.md",
        lineterm="",
    )
    diff = list(diff_generator)

    return {"task1_id": task1_id, "task2_id": task2_id, "diff": diff}
