# aegis/utils/replay_logger.py
"""
A simple utility for logging events for task replay and debugging.
"""
import json
from pathlib import Path
from typing import Any

from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

config = get_config()
REPORTS_BASE_DIR = Path(config.get("paths", {}).get("reports", "reports"))


def log_replay_event(task_id: str, event_type: str, data: Any):
    """
    Appends a structured event to the task's replay.jsonl file.

    :param task_id: The ID of the current task.
    :type task_id: str
    :param event_type: The type of event being logged (e.g., 'PLANNER_INPUT').
    :type event_type: str
    :param data: The data payload for the event (must be JSON-serializable).
    :type data: Any
    """
    try:
        reports_dir = REPORTS_BASE_DIR / task_id
        reports_dir.mkdir(parents=True, exist_ok=True)
        replay_log_path = reports_dir / "replay.jsonl"

        log_entry = {"event_type": event_type, "data": data}

        with replay_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")
    except Exception as e:
        logger.error(
            f"Failed to write to replay log for task {task_id}. Event: {event_type}. Error: {e}"
        )
