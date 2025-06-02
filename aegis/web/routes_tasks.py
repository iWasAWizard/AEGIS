"""Provides task-level CRUD and status endpoints for managing active or historical agent tasks."""

import os

from fastapi import APIRouter

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.get("/tasks")
async def list_tasks():
    """
    list_tasks.
    :return: Description of return value
    :rtype: Any
    """
    logger.info("→ [routes_tasks] Entering def()")
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        logger.warning("[inventory] Reports directory does not exist.")
        return []
    task_ids = [
        name
        for name in os.listdir(reports_dir)
        if os.path.isdir(os.path.join(reports_dir, name))
    ]
    logger.info(f"[inventory] Found {len(task_ids)} task(s).")
    logger.debug(f"[inventory] Task IDs: {task_ids}")
    return sorted(task_ids, reverse=True)
