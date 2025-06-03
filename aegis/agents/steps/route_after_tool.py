"""
Determines the next routing step based on the results of the previous tool execution.
"""

from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def route_after_tool(state: TaskState) -> TaskState:
    """
    Determines the next step in the graph based on the output of the last tool.

    Sets the `next_step` field on the TaskState for dynamic routing.

    :param state: Current task state
    :type state: TaskState
    :return: Modified task state with next_step set
    :rtype: TaskState
    """
    logger.info("Determining next routing step")

    if not state.tool_name:
        logger.warning("No tool_name available in state; cannot route")
        state.next_step = "reflect_and_plan"
        return state

    result = state.steps_output.get(state.tool_name)
    if result is None:
        logger.warning(f"No output recorded for tool: {state.tool_name}")
        state.next_step = "reflect_and_plan"
        return state

    logger.debug(f"Tool output: {result}")
    state.next_step = "summarize_result"
    return state
