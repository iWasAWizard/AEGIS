"""
Evaluates whether the agent should halt execution due to max steps or an explicit termination reason.
"""

from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
MAX_STEPS = 20


async def check_termination(state: TaskState) -> str:
    """
    Determines if the task should terminate based on internal state conditions.

    :param state: Task execution state
    :type state: TaskState
    :return: Next step identifier ("complete" or "reflect")
    :rtype: str
    """
    logger.info("Checking if task should terminate...")
    logger.debug(
        f"Steps taken: {state.steps_taken}, Terminate reason: {state.terminate_reason}"
    )

    if state.terminate_reason:
        logger.info(
            f"Task {state.task_id} already marked complete: {state.terminate_reason}"
        )
        return "complete"

    if state.steps_taken >= MAX_STEPS:
        logger.info(f"Max steps reached for task {state.task_id}")
        return "complete"

    logger.info(
        f"Task '{state.task_id}' has not met termination criteria. Proceeding to next step."
    )
    return "reflect"
