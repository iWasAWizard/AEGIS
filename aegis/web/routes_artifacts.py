# aegis/web/routes_artifacts.py
"""
API route for listing and managing task artifacts and reports.
"""

from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter

from aegis.utils.logger import setup_logger

router = APIRouter()
REPORTS_DIR = Path("reports")
logger = setup_logger(__name__)


@router.get("/artifacts", tags=["Artifacts"])
async def list_artifacts() -> List[Dict[str, Any]]:
    """Scans the reports directory and lists all found task artifacts.

    For each task ID (subdirectory), it identifies key artifacts like the
    final summary markdown file.

    :return: A list of dictionaries, each representing a task and its artifacts.
    :rtype: List[Dict[str, Any]]
    """
    logger.info("Artifact list requested. Scanning reports directory.")
    if not REPORTS_DIR.exists() or not REPORTS_DIR.is_dir():
        logger.warning(f"Reports directory '{REPORTS_DIR}' does not exist.")
        return []

    results: List[Dict[str, Any]] = []
    for task_dir in sorted(REPORTS_DIR.iterdir(), reverse=True):
        if task_dir.is_dir():
            summary_path = task_dir / "summary.md"
            results.append(
                {
                    "task_id": task_dir.name,
                    "has_summary": summary_path.exists(),
                    "summary_path": (
                        str(summary_path) if summary_path.exists() else None
                    ),
                }
            )
    return results
