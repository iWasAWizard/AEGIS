# aegis/agents/steps/execute_tool.py
"""
The core tool execution step for the agent.

This module contains the `execute_tool` function, which is responsible for
looking up a tool in the registry, validating its arguments, running it, and
recording the results in a structured history entry.
"""

import asyncio
import time
from typing import Dict, Any, Callable, Literal

from pydantic import ValidationError

from aegis.agents.task_state import HistoryEntry, TaskState
from aegis.exceptions import ToolExecutionError, ToolNotFoundError
from aegis.registry import get_tool
from aegis.utils.logger import setup_logger
from schemas.plan_output import AgentScratchpad

logger = setup_logger(__name__)


async def _run_tool(tool_func: Callable, input_data: Any) -> Any:
    """Helper to run the tool's function, which might be a coroutine.

    :param tool_func: The tool's function to be executed.
    :type tool_func: Callable
    :param input_data: The validated Pydantic model instance for the tool.
    :type input_data: Any
    :return: The output from the tool execution.
    :rtype: Any
    """
    if asyncio.iscoroutinefunction(tool_func):
        return await tool_func(input_data)
    else:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, tool_func, input_data)


async def execute_tool(state: TaskState) -> Dict[str, Any]:
    """Looks up and executes a tool, then records a structured HistoryEntry.

    :param state: The current state of the agent's task.
    :type state: TaskState
    :return: A dictionary with the updated history.
    :rtype: Dict[str, Any]
    """
    logger.info("🛠️ Step: Execute Tool")
    start_time = time.time()
    plan = state.latest_plan

    # This should ideally not be hit if the graph is well-formed, but is a safeguard.
    if not plan:
        error_msg = "[ERROR] Execution failed: No plan found in state."
        logger.error(error_msg, extra={"event_type": "InternalError", "reason": "Missing plan"})
        plan = AgentScratchpad(
            thought="No plan was provided to the executor.",
            tool_name="finish",
            tool_args={"reason": "Internal error: missing plan.", "status": "failure"},
        )
        entry = HistoryEntry(plan=plan, observation=error_msg, status="failure", start_time=start_time,
                             end_time=time.time())
        return {"history": state.history + [entry]}

    tool_name = plan.tool_name
    tool_args = plan.tool_args
    tool_output: Any
    status: Literal["success", "failure"] = "success"

    logger.info(
        f"Executing tool: `{tool_name}`",
        extra={"event_type": "ToolStart", "tool_name": tool_name, "tool_args": tool_args},
    )

    if tool_name == "finish":
        tool_output = f"Task finished by agent with reason: {tool_args.get('reason', 'No reason given.')}"
    else:
        try:
            tool_entry = get_tool(tool_name, safe_mode=state.runtime.safe_mode)
            input_model = tool_entry.input_model(**tool_args)
            tool_output = await asyncio.wait_for(
                _run_tool(tool_entry.run, input_model),
                timeout=state.runtime.timeout,
            )
        except ToolNotFoundError as e:
            tool_output = f"[ERROR] Tool lookup failed: {e}"
        except ValidationError as e:
            tool_output = f"[ERROR] Input validation failed for tool '{tool_name}': {e}"
        except asyncio.TimeoutError:
            tool_output = f"[ERROR] Tool '{tool_name}' timed out after {state.runtime.timeout} seconds."
        except Exception as e:
            wrapped_error = ToolExecutionError(f"Tool '{tool_name}' failed during execution: {e}")
            tool_output = f"[ERROR] {wrapped_error}"

    # Determine status and log accordingly
    if isinstance(tool_output, str) and tool_output.startswith("[ERROR]"):
        status = "failure"
        logger.error(
            f"Tool `{tool_name}` failed.",
            extra={"event_type": "ToolEnd", "tool_name": tool_name, "status": "failure", "error_message": tool_output},
        )
    else:
        logger.info(
            f"Tool `{tool_name}` executed successfully.",
            extra={"event_type": "ToolEnd", "tool_name": tool_name, "status": "success",
                   "output_preview": str(tool_output)[:200]},
        )

    end_time = time.time()

    # Create the structured history entry
    history_entry = HistoryEntry(
        plan=plan,
        observation=tool_output,
        status=status,
        start_time=start_time,
        end_time=end_time,
        duration_ms=(end_time - start_time) * 1000,
    )

    new_history = state.history + [history_entry]
    return {"history": new_history}
