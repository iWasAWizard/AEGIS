# aegis/agents/steps/check_termination.py
"""
The termination and routing step for the agent graph.

This function acts as the main conditional router. It inspects the agent's
state after each tool execution to decide whether to continue the loop or
to terminate the task.
"""

from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def check_termination(state: TaskState) -> str:
    """Determines if the agent should continue, interrupt, or end the task.

    This function acts as a conditional edge in the graph. It checks for
    a 'finish' tool call, an 'ask_human_for_input' call, or if the step
    limit has been reached.

    :param state: The current state of the agent's task.
    :type state: TaskState
    :return: A routing string: 'continue', 'interrupt', or 'end'.
    :rtype: str
    """
    logger.info("✅ Step: Check for Termination")
    logger.debug(
        f"Current state: steps_taken={state.steps_taken}, max_iterations={state.runtime.iterations}"
    )

    if not state.history:
        return "continue"

    last_tool_name = state.history[-1].plan.tool_name

    # Condition 1: Check if the last planned tool was 'finish'.
    if last_tool_name == "finish":
        logger.info("Termination condition met: 'finish' tool was called.")
        return "end"

    # Condition 2: Check if the last tool was a request for human input.
    if last_tool_name == "ask_human_for_input":
        logger.info("Interrupt condition met: 'ask_human_for_input' tool was called.")
        return "interrupt"

    # Condition 3: Check if the maximum number of steps has been reached.
    max_steps = state.runtime.iterations
    if max_steps is not None and state.steps_taken >= max_steps:
        logger.warning(f"Termination condition met: Max steps ({max_steps}) reached.")
        return "end"

    # If no termination conditions are met, continue the loop.
    logger.info("No termination condition met. Continuing to next planning step.")
    return "continue"
