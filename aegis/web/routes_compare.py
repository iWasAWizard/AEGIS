# aegis/web/routes_compare.py
"""
API route for comparing artifacts from two different task runs.
"""

import difflib
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Body

from aegis.utils.logger import setup_logger

router = APIRouter()
REPORTS_DIR = Path("reports")
logger = setup_logger(__name__)


@router.post("/compare_reports", tags=["Artifacts"])
async def compare_task_summaries(task_ids: List[str] = Body(...)) -> dict:
    """Compares the summary.md files of two tasks and returns a diff.

    This endpoint takes a list of two task IDs, reads their corresponding
    `summary.md` files, and generates a unified diff of their contents. This
    is useful for comparing the outcomes of two different agent runs.

    :param task_ids: A list containing exactly two task IDs.
    :type task_ids: List[str]
    :return: A dictionary containing the task IDs and the generated diff.
    :rtype: dict
    :raises HTTPException: If inputs are invalid or files cannot be processed.
    """
    if len(task_ids) != 2:
        logger.warning(
            f"Compare request failed: expected 2 task IDs, got {len(task_ids)}."
        )
        raise HTTPException(
            status_code=400, detail="Please provide exactly two task IDs to compare."
        )

    task1_id, task2_id = task_ids[0], task_ids[1]
    logger.info(f"Compare request received for tasks: {task1_id} vs {task2_id}")

    summary1_path = REPORTS_DIR / task1_id / "summary.md"
    summary2_path = REPORTS_DIR / task2_id / "summary.md"

    if not summary1_path.is_file():
        logger.error(
            f"Comparison failed: summary for task '{task1_id}' not found at {summary1_path}"
        )
        raise HTTPException(
            status_code=404, detail=f"Summary for task '{task1_id}' not found."
        )
    if not summary2_path.is_file():
        logger.error(
            f"Comparison failed: summary for task '{task2_id}' not found at {summary2_path}"
        )
        raise HTTPException(
            status_code=404, detail=f"Summary for task '{task2_id}' not found."
        )

    try:
        lines1 = summary1_path.read_text(encoding="utf-8").splitlines()
        lines2 = summary2_path.read_text(encoding="utf-8").splitlines()
    except IOError as e:
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
    logger.info(f"Comparison successful, diff generated with {len(diff)} lines.")
    return {"task1_id": task1_id, "task2_id": task2_id, "diff": diff}
