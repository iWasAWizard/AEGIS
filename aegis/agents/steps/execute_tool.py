# aegis/agents/steps/execute_tool.py
"""
The core tool execution step for the agent.

This module contains the `execute_tool` function, which is responsible for
looking up a tool in the registry, validating its arguments, and running it.
It then appends the full record of this step to the agent's history.
"""

import asyncio
from typing import Dict, Any, Coroutine, List, Tuple

from aegis.agents.plan_output import AgentScratchpad
from aegis.agents.task_state import TaskState
from aegis.registry import get_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


async def _run_tool(tool_func: Coroutine, input_data: Any) -> Any:
    """Helper to run the tool's function, which might be a coroutine."""
    if asyncio.iscoroutinefunction(tool_func):
        return await tool_func(input_data)
    else:
        # For regular functions, run them in a default executor to avoid blocking the event loop.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, tool_func, input_data)


async def execute_tool(state: TaskState) -> Dict[str, Any]:
    """Looks up and executes the tool from the latest plan, then updates history.

    :param state: The current state of the agent's task.
    :type state: TaskState
    :return: A dictionary with the updated history.
    :rtype: Dict[str, Any]
    """
    logger.info("🛠️ Step: Execute Tool")
    plan = state.latest_plan

    if not plan:
        error_msg = "[ERROR] Execution failed: No plan found in state."
        logger.error(
            error_msg, extra={"event_type": "InternalError", "reason": "Missing plan"}
        )
        # Create a dummy plan to record the failure in history
        plan = AgentScratchpad(
            thought="No plan was provided to the executor.",
            tool_name="finish",
            tool_args={"reason": "Internal error: missing plan.", "status": "failure"},
        )
        return {"history": state.history + [(plan, error_msg)]}

    tool_name = plan.tool_name
    tool_args = plan.tool_args
    tool_output: Any

    # Structured log event for starting a tool
    logger.info(
        f"Executing tool: `{tool_name}`",
        extra={
            "event_type": "ToolStart",
            "tool_name": tool_name,
            "tool_args": tool_args,
        },
    )

    if tool_name == "finish":
        tool_output = f"Task finished by agent with reason: {tool_args.get('reason', 'No reason given.')}"
    else:
        tool_entry = get_tool(tool_name, safe_mode=state.runtime.safe_mode)
        if not tool_entry:
            tool_output = (
                f"[ERROR] Tool `{tool_name}` not found or not permitted in safe mode."
            )
            logger.error(
                tool_output, extra={"event_type": "ToolError", "tool_name": tool_name}
            )
        else:
            try:
                input_model = tool_entry.input_model(**tool_args)
                tool_output = await asyncio.wait_for(
                    _run_tool(tool_entry.run, input_model),
                    timeout=state.runtime.timeout,
                )
                # Structured log event for tool success
                logger.info(
                    f"Tool `{tool_name}` executed successfully.",
                    extra={
                        "event_type": "ToolEnd",
                        "tool_name": tool_name,
                        "status": "success",
                        "output_preview": str(tool_output)[:200],
                    },
                )
            except Exception as e:
                tool_output = f"[ERROR] Tool `{tool_name}` failed during execution: {e}"
                # Structured log event for tool failure
                logger.exception(
                    tool_output,
                    extra={
                        "event_type": "ToolEnd",
                        "tool_name": tool_name,
                        "status": "failure",
                        "error_message": str(e),
                    },
                )

    # Append the completed step (plan + result) to the history
    new_history: List[Tuple[AgentScratchpad, Any]] = state.history + [
        (plan, tool_output)
    ]
    return {"history": new_history}
