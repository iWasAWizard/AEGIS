# aegis/utils/procedure.py
"""DEPRECATED - Loads multi-step procedures and saves them as CSV files.

This module's functionality has been superseded by the more robust and detailed
`provenance.py` and `markdown.py` reporting utilities. It is kept for
historical reference but is no longer used.
"""

import csv
import json
from typing import List

from aegis.agents.task_state import HistoryEntry
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def save_procedure_csv(history: List[HistoryEntry], path: str):
    """Saves a task's execution steps to a CSV file.

    :param history: A list of `HistoryEntry` objects from a completed task.
    :type history: List[HistoryEntry]
    :param path: The filesystem path where the CSV will be written.
    :type path: str
    """
    logger.info(f"Saving execution procedure as CSV to: {path}")
    if not history:
        logger.warning("No history entries found; cannot generate a procedure CSV.")
        return

    try:
        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Step", "Tool Name", "Tool Arguments", "Observation"])
            for i, entry in enumerate(history):
                # Serialize args to a compact JSON string for readability in the CSV
                args_str = json.dumps(entry.plan.tool_args)
                writer.writerow([
                    i + 1,
                    entry.plan.tool_name,
                    args_str,
                    str(entry.observation),
                ])
        logger.info(f"Procedure CSV saved successfully.")
    except IOError as e:
        logger.exception(f"Failed to write procedure CSV to {path}: {e}")
