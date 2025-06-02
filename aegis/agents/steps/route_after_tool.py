"""
Node step for analyzing the last tool output and determining whether to replan or proceed.
"""

from aegis.agents.task_state import TaskState
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


async def route_after_tool(state: TaskState) -> TaskState:
    """
    route_after_tool.
    :param state: Description of state
    :type state: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("🔁 Routing after tool execution")
    output = state.last_tool_output or ""
    logger.debug(f"Last tool output: {output}")
    if "service not running" in output.lower():
        logger.warning("Detected service down. Re-planning.")
        state = state.update(tool_request=None)
    elif "connection refused" in output.lower():
        logger.warning("Connection issue detected. Re-planning.")
        state = state.update(tool_request=None)
    else:
        logger.info("Tool executed successfully. Proceeding to summarization.")
    logger.debug(f"Updated state: {state.pretty_json()}")
    return state
