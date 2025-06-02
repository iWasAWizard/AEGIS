from aegis.agents.task_state import TaskState
from aegis.registry import TOOL_REGISTRY
from aegis.types import ToolCall
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def execution_node(state: TaskState) -> TaskState:
    """
    Pops the next ToolCall from the execution plan and runs it.
    """
    state.event_log.append("execution")

    if not state.execution_plan:
        logger.warning("Execution plan is empty. Nothing to execute.")
        return state

    tool_call: ToolCall = state.execution_plan.pop(0)
    tool_name = tool_call.tool
    tool_input = tool_call.input

    logger.info(f"Executing tool: {tool_name}")
    logger.debug(f"Tool input: {tool_input}")

    if tool_name not in TOOL_REGISTRY:
        logger.error(f"Tool not found: {tool_name}")
        state.journal += f"\n[Error] Tool not found: {tool_name}"
        return state

    try:
        tool = TOOL_REGISTRY[tool_name].tool
        result = tool(tool_input)
        logger.debug(f"Tool result: {result}")
        state.journal += f"\n[{tool_name}] {result}"
    except Exception as e:
        logger.exception("Tool execution failed")
        state.journal += f"\n[Error executing {tool_name}]: {str(e)}"

    return state
