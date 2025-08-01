# aegis/web/routes_artifacts.py
"""
API routes for listing and managing task artifacts and reports.

This module provides endpoints for the web UI to discover and retrieve the
outputs generated by completed agent tasks, such as summaries and provenance logs.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from aegis.utils.logger import setup_logger

router = APIRouter()
REPORTS_DIR = Path("reports")
logger = setup_logger(__name__)


@router.get("/artifacts", tags=["Artifacts"])
async def list_artifacts() -> List[Dict[str, Any]]:
    """Scans the reports directory and lists all found task artifacts.

    This endpoint iterates through the subdirectories of the `reports/` directory,
    treating each subdirectory name as a `task_id`. It checks for the presence
    of key artifact files (`summary.md`, `provenance.json`) and returns a list
    of metadata objects for the UI.
    """
    logger.info("Artifact list requested. Scanning reports directory.")
    if not REPORTS_DIR.exists() or not REPORTS_DIR.is_dir():
        logger.warning(f"Reports directory '{REPORTS_DIR}' does not exist.")
        return []

    results: List[Dict[str, Any]] = []
    task_dirs = sorted(
        REPORTS_DIR.iterdir(), key=lambda n: n.stat().st_mtime, reverse=True
    )

    for task_dir in task_dirs:
        if task_dir.is_dir():
            task_id = task_dir.name
            prompt = "N/A"
            final_status = "UNKNOWN"
            provenance_path = task_dir / "provenance.json"

            if provenance_path.is_file():
                try:
                    with provenance_path.open("r", encoding="utf-8") as f:
                        prov_data = json.load(f)
                        prompt = prov_data.get("task_prompt", "Prompt not found.")
                        final_status = prov_data.get("final_status", "UNKNOWN")
                except (IOError, json.JSONDecodeError):
                    logger.warning(f"Could not read or parse provenance for {task_id}")

            results.append(
                {
                    "task_id": task_id,
                    "prompt": prompt,
                    "final_status": final_status,
                    "has_summary": (task_dir / "summary.md").exists(),
                    "has_provenance": provenance_path.exists(),
                    "timestamp": task_dir.stat().st_mtime,
                }
            )

    logger.info(f"Found {len(results)} tasks with artifacts.")
    return results


@router.get(
    "/artifacts/{task_id}/summary", tags=["Artifacts"], response_class=PlainTextResponse
)
async def get_summary_artifact(task_id: str):
    """Retrieves the content of a task's summary.md file.

    :param task_id: The ID of the task to retrieve the summary for.
    :type task_id: str
    :return: The raw Markdown content of the summary file.
    :rtype: PlainTextResponse
    :raises HTTPException: If the summary file is not found.
    """
    logger.info(f"Request for summary artifact for task: {task_id}")
    summary_path = REPORTS_DIR / task_id / "summary.md"
    if not summary_path.is_file():
        logger.error(f"Summary file not found for task '{task_id}' at {summary_path}")
        raise HTTPException(status_code=404, detail="Summary artifact not found.")
    try:
        return summary_path.read_text(encoding="utf-8")
    except IOError as e:
        logger.exception(f"Could not read summary file for task '{task_id}'")
        raise HTTPException(status_code=500, detail=f"Error reading summary file: {e}")


@router.get("/artifacts/{task_id}/provenance", tags=["Artifacts"])
async def get_provenance_artifact(task_id: str):
    """Retrieves the content of a task's provenance.json file.

    :param task_id: The ID of the task to retrieve the provenance for.
    :type task_id: str
    :return: The parsed JSON content of the provenance file.
    :rtype: dict
    :raises HTTPException: If the provenance file is not found or is invalid JSON.
    """
    logger.info(f"Request for provenance artifact for task: {task_id}")
    provenance_path = REPORTS_DIR / task_id / "provenance.json"
    if not provenance_path.is_file():
        logger.error(
            f"Provenance file not found for task '{task_id}' at {provenance_path}"
        )
        raise HTTPException(status_code=404, detail="Provenance artifact not found.")
    try:
        with provenance_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.exception(
            f"Could not read or parse provenance file for task '{task_id}'"
        )
        raise HTTPException(
            status_code=500, detail=f"Error reading or parsing provenance file: {e}"
        )
