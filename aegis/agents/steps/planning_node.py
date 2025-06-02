import json

from aegis.agents.task_state import TaskState
from aegis.registry import TOOL_REGISTRY
from aegis.types import ToolCall
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def plan_tool_invocations(state: TaskState) -> list[ToolCall]:
    """
    Generate a list of tool calls from the LLM to accomplish the current goal.
    """
    system_prompt = (
        "You are a reasoning engine responsible for planning a series of tools to accomplish a goal.\n"
        "Output a list of tool invocations in JSON. Each item must contain:\n"
        "- tool: name of the tool to invoke\n"
        "- input: dictionary of inputs matching the tool’s schema\n\n"
        "Only use tools that are currently available. No commentary."
    )

    tool_names = sorted(TOOL_REGISTRY.keys())
    user_prompt = (
        f"Available tools: {tool_names}\n"
        f"Goal: {state.goal}\n"
        f"Context: {state.journal}\n"
        f"Respond with JSON only."
    )

    logger.info("LLM planning invocation")
    raw_response = llm_query(system_prompt, user_prompt)
    logger.debug(f"Raw planning response: {raw_response}")

    try:
        calls = json.loads(raw_response)
        return [ToolCall(tool=item["tool"], input=item["input"]) for item in calls]
    except Exception as e:
        logger.exception("Failed to parse planning output")
        raise RuntimeError(f"Planning error: {e}")


def planning_node(state: TaskState) -> TaskState:
    """
    LangGraph-compatible planning node that updates the execution plan.
    """
    state.event_log.append("planning")
    tool_calls = plan_tool_invocations(state)
    state.execution_plan.extend(tool_calls)
    return state
