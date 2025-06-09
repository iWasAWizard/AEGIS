# aegis/utils/timeline.py
"""DEPRECATED - Builds a sequential timeline of agent task execution.

This module's functionality has been superseded by the more detailed and
robust `provenance.py` reporting utility. It is kept for historical
reference but is no longer used.
"""
from typing import List

import matplotlib.pyplot as plt

from aegis.agents.task_state import HistoryEntry
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def save_timeline_plot(history: List[HistoryEntry], path: str):
    """Saves a bar chart visualization of task step durations.

    :param history: A list of `HistoryEntry` objects from a completed task.
    :type history: List[HistoryEntry]
    :param path: The filesystem path where the plot image will be saved.
    :type path: str
    """
    logger.info(f"Generating and saving execution timeline plot to: {path}")

    if not history:
        logger.warning("No history entries found; cannot generate a timeline plot.")
        return

    labels = [f"Step {i + 1}: {entry.plan.tool_name}" for i, entry in enumerate(history)]
    # Durations are in milliseconds, convert to seconds for the plot
    durations_sec = [entry.duration_ms / 1000 for entry in history]

    try:
        plt.figure(figsize=(10, len(history) * 0.5 + 2))  # Dynamic height
        plt.barh(labels, durations_sec, color='#3b82f6', edgecolor='#444')

        # Add duration labels to the bars
        for index, value in enumerate(durations_sec):
            plt.text(value, index, f' {value:.2f}s', va='center')

        plt.xlabel("Duration (seconds)")
        plt.ylabel("Agent Step")
        plt.title("Agent Task Execution Timeline")
        plt.gca().invert_yaxis()  # Display Step 1 at the top
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        logger.info(f"Timeline plot saved successfully.")
    except IOError as e:
        logger.exception(f"Failed to save timeline plot to '{path}': {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred while generating timeline plot: {e}")
