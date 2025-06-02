"""Records detailed logs of task execution, tool responses, and system behaviors.
Useful for auditing, debugging, and agent observability."""

import json
import os
from datetime import datetime

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def log_event(task_id: str, event: dict, logs_dir: str = "logs") -> None:
    """
    Appends a JSON event to the task-specific log file.
    """
    os.makedirs(logs_dir, exist_ok=True)
    logger.debug("Artifact directory created")
    log_path = os.path.join(logs_dir, f"{task_id}.jsonl")

    # Timestamp the event
    event["ts"] = datetime.utcnow().isoformat() + "Z"

    with open(log_path, "a") as f:
        f.write(json.dumps(event) + "\n")
    logger.info("Task log written")
