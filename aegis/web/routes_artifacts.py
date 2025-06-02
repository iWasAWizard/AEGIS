"""
Artifact route for listing output summaries or generated files.
"""

from pathlib import Path

from fastapi import APIRouter

from aegis.utils.logger import setup_logger

router = APIRouter()
REPORTS_DIR = Path("reports")
logger = setup_logger(__name__)


@router.get("/artifacts")
async def list_artifacts():
    """
    list_artifacts.
    :return: Description of return value
    :rtype: Any
    """
    logger.info("→ [routes_artifacts] Entering def()")
    if not REPORTS_DIR.exists():
        logger.warning("[routes_artifacts] Reports directory does not exist.")
        return []
    result = []
    for task_dir in REPORTS_DIR.iterdir():
        if task_dir.is_dir():
            summary = task_dir / "summary.md"
            result.append(
                {
                    "task_id": task_dir.name,
                    "has_summary": summary.exists(),
                    "path": str(summary) if summary.exists() else None,
                }
            )
    return result
