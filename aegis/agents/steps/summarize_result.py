"""
Summarizes the final result of the agent's workflow and updates the task journal.
"""

from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def summarize_result(state: TaskState) -> TaskState:
    """
    Summarizes the results from the agent's execution and appends it to the journal.

    :param state: Current task state
    :type state: TaskState
    :return: Task state with summary updated
    :rtype: TaskState
    """
    logger.info("Running summarize_result step")

    if not state.steps_output:
        logger.warning("No steps_output to summarize")
        summary = "No steps were executed."
    else:
        summary_lines = [
            f"{tool}: {output}" for tool, output in state.steps_output.items()
        ]
        summary = "\n".join(summary_lines)

    logger.debug(f"Generated summary:\n{summary}")
    state.journal += f"\n\n[Summary]\n{summary}"
    return state
