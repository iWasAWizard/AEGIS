# aegis/web/routes_reports.py
"""Routes for accessing agent execution reports, markdown summaries, and result artifacts."""

import os

from fastapi import APIRouter, HTTPException

from aegis.utils.logger import setup_logger

REPORT_DIR = "reports"
router = APIRouter(prefix="/reports", tags=["reports"])
logger = setup_logger(__name__)


@router.get("/", summary="List all generated reports")
def list_reports() -> list[str]:
    """Lists the names of all available report files (md, txt, html) in the root reports directory.

    Note: This is a legacy endpoint. Newer, more structured artifacts are accessed
    via the `/artifacts` routes.

    :return: A sorted list of report filenames.
    :rtype: list[str]
    """
    logger.info("Request received to list all reports.")
    if not os.path.exists(REPORT_DIR):
        logger.warning(f"Reports directory '{REPORT_DIR}' not found.")
        return []

    reports = sorted(
        f for f in os.listdir(REPORT_DIR)
        if f.endswith((".md", ".txt", ".html"))
    )
    logger.info(f"Found {len(reports)} reports in directory.")
    return reports


@router.get("/view", summary="View a specific report")
def view_report(name: str) -> dict:
    """Retrieves the contents of a saved report file from the root reports directory.

    Note: This is a legacy endpoint. Newer, more structured artifacts are accessed
    via the `/artifacts` routes.

    :param name: The filename of the report to view.
    :type name: str
    :return: A dictionary containing the raw report text.
    :rtype: dict
    :raises HTTPException: If the file does not exist or is unreadable.
    """
    logger.info(f"Request received to view report: '{name}'")
    path = os.path.join(REPORT_DIR, name)

    if not os.path.exists(path):
        logger.error(f"Report not found at path: {path}")
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Successfully read report: '{name}'")
        return {"content": content}
    except IOError as e:
        logger.exception(f"Could not read report file at '{path}': {e}")
        raise HTTPException(status_code=500, detail=f"Could not read report file: {e}")
