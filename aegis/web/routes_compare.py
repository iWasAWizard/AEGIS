"""
Compare route to diff two task summaries.
"""

import difflib
from pathlib import Path

from fastapi import APIRouter, HTTPException

from aegis.utils.logger import setup_logger

router = APIRouter()
REPORTS_DIR = Path("reports")
logger = setup_logger(__name__)


@router.get("/compare")
async def compare_artifacts(task1: str, task2: str):
    """
    compare_artifacts.
    :param task1: Description of task1
    :param task2: Description of task2
    :type task1: Any
    :type task2: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("→ [routes_compare] Entering def()")
    summary1 = REPORTS_DIR / task1 / "summary.md"
    summary2 = REPORTS_DIR / task2 / "summary.md"
    if not summary1.exists() or not summary2.exists():
        raise HTTPException(status_code=404, detail="One or both summaries not found.")
    lines1 = summary1.read_text().splitlines()
    lines2 = summary2.read_text().splitlines()
    diff = list(difflib.unified_diff(lines1, lines2, fromfile=task1, tofile=task2))
    return {"task1": task1, "task2": task2, "diff": diff}
