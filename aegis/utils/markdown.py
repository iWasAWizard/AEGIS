# aegis/utils/markdown.py
"""Provides utility functions for manipulating and generating Markdown content.

This module is used to structure outputs, format logs, and create human-readable
reports from the agent's execution history.
"""

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def save_markdown_report(state: dict, path: str) -> None:
    """Saves a markdown-formatted task report to the given path.

    This function takes a state dictionary, which is expected to contain details
    of a completed task, and formats it into a structured Markdown file.

    :param state: A dictionary containing task details, like 'task', 'task_id', and 'result'.
                  The 'result' key should contain a list of step dictionaries.
    :type state: dict
    :param path: The filesystem path where the report will be written.
    :type path: str
    """
    logger.info(f"Saving markdown report to: {path}")
    logger.debug(f"Report metadata: task_id={state.get('task_id')}")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Task Report\n\n")
            f.write(f"**Task:** {state.get('task')}\n\n")
            f.write(f"**Task ID:** {state.get('task_id')}\n\n")
            f.write("---\n\n")
            for result in state.get("result", []):
                f.write("### Step\n")
                f.write(f"**Tool:** `{result.get('tool')}`\n\n")
                f.write(f"**Command:**\n```\n{result.get('command', 'N/A')}\n```\n\n")
                f.write(f"**Output:**\n```\n{result.get('stdout', 'N/A')}\n```\n\n")
    except IOError as e:
        logger.exception(f"Failed to write markdown report to {path}: {e}")
