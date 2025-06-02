from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
MAX_STEPS = 20


async def check_termination(state: TaskState) -> str:
    """
    check_termination.
    :param state: Description of state
    :type state: Any
    :return: Description of return value
    :rtype: Any
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
