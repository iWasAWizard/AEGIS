"""Provides utility functions for manipulating and validating Markdown content.
Used to structure outputs, format logs, and embed tool responses."""

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def save_markdown_report(state, path):
    """
    Save a markdown-formatted task report to the given path.

    :param state: Dictionary containing task, task_id, and result steps
    :param path: Filesystem path to write the report to
    """
    logger.info(f"Saving markdown report to {path}")
    logger.debug(f"Report metadata: task={state.get('task')}, task_id={state.get('task_id')}")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Task Report\n\n")
            f.write(f"**Task:** {state.get('task')}\n\n")
            f.write(f"**Task ID:** {state.get('task_id')}\n\n")
            for result in state.get("result", []):
                f.write("### Step\n")
                f.write(f"**Tool:** {result.get('tool')}\n\n")
                f.write(f"**Command:** `{result.get('command')}`\n\n")
                f.write(f"**Output:**\n```\n{result.get('stdout')}\n```\n\n")
    except IOError:
        logger.exception(f"Failed to write markdown report to {path}")
