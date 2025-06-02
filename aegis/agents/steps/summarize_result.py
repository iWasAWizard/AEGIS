"""Node step for creating a final markdown summary file based on task execution results."""

import os

from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


async def summarize_result(state: TaskState) -> TaskState:
    """
    summarize_result.
    :param state: Description of state
    :type state: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("Running summarize_result step")
    logger.debug("Generating task summary")
    try:
        output_dir = os.path.join("reports", state.task_id)
        os.makedirs(output_dir, exist_ok=True)
        logger.debug(f"Created or reused output directory: {output_dir}")
        summary_path = os.path.join(output_dir, "summary.md")
        with open(summary_path, "w") as f:
            summary = f"## Task Summary" \
                      f"" \
                      f"**Prompt**: {state.task_prompt}" \
                      f"" \
                      f"" \
                      f"                      **Plan**: {state.plan}" \
                      f"" \
                      f"**Results**:" \
                      f"{state.results}" \
                      f"" \
                      f"" \
                      f"                      **Final Output**:" \
                      f"{state.last_tool_output}"
            f.write(summary)
        logger.info(f"Summary written to: {summary_path}")
        updated_state = state.update(summary=summary_path)
        logger.debug(f"Updated state: {updated_state.pretty_json()}")
        return updated_state
    except Exception as e:
        logger.exception("Failed to write summary file")
        return state.update(error=str(e))
