"""Routes for accessing agent execution reports, markdown summaries, and result artifacts."""

import os

from fastapi import APIRouter, HTTPException

from aegis.utils.logger import setup_logger

REPORT_DIR = "reports"
router = APIRouter(prefix="/reports", tags=["reports"])
logger = setup_logger(__name__)


@router.get("/", summary="List all generated reports")
def list_reports():
    """
    List the names of all available reports.

    :return: Sorted list of report filenames
    :rtype: List[str]
    """
    logger.info("Listing reports")
    if not os.path.exists(REPORT_DIR):
        return []
    return sorted(
        (
            f
            for f in os.listdir(REPORT_DIR)
            if f.endswith(".md") or f.endswith(".txt") or f.endswith(".html")
        )
    )


@router.get("/view", summary="View a specific report")
def view_report(name: str):
    """
    Retrieve the contents of a saved report file.

    :param name: The filename of the report to view
    :type name: str
    :return: Dictionary containing the raw report text
    :rtype: dict
    :raises HTTPException: if the file does not exist
    """
    logger.info(f"Viewing report: {name}")
    path = os.path.join(REPORT_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    with open(path, "r", encoding="utf-8") as f:
        return {"content": f.read()}
