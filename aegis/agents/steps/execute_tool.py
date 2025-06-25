# aegis/agents/steps/execute_tool.py
"""
The core tool execution step for the agent.

This module contains the `execute_tool` function, which is responsible for
looking up a tool in the registry, validating its arguments, running it, and
recording the results in a structured history entry.
"""

import asyncio
import inspect
import json
import time
from typing import Dict, Any, Callable, Literal

from pydantic import ValidationError

from aegis.agents.task_state import HistoryEntry, TaskState
from aegis.exceptions import ToolExecutionError, ToolNotFoundError
from aegis.registry import get_tool
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


async def _run_tool(tool_func: Callable, input_data: Any, state: TaskState) -> Any:
    """
    Helper to run the tool's function, inspecting its signature to see if it
    needs the state or provider passed to it.
    """
    sig = inspect.signature(tool_func)
    
    # Prepare arguments for the tool call
    tool_kwargs = {"input_data": input_data}

    if "state" in sig.parameters:
        tool_kwargs["state"] = state
    if "provider" in sig.parameters:
        # Resolve the provider only if the tool needs it
        provider = get_provider_for_profile(state.runtime.backend_profile)
        tool_kwargs["provider"] = provider

    if asyncio.iscoroutinefunction(tool_func):
        return await tool_func(**tool_kwargs)
    else:
        loop = asyncio.get_running_loop()
        # Use a lambda to pass kwargs to the executor
        return await loop.run_in_executor(None, lambda: tool_func(**tool_kwargs))


async def execute_tool(state: TaskState) -> Dict[str, Any]:
    """Looks up and executes a tool, then records a structured HistoryEntry."""
    logger.info("🛠️  Step: Execute Tool")
    logger.debug(f"Entering execute_tool with state: {repr(state)}")
    start_time = time.time()
    plan = state.latest_plan

    if not plan:
        error_msg = "[ERROR] Execution failed: No plan found in state."
        logger.error(error_msg, extra={"event_type": "InternalError", "reason": "Missing plan"})
        plan = AgentScratchpad(
            thought="Critical error: No plan was provided to the executor step. Terminating task.",
            tool_name="finish",
            tool_args={"reason": "Internal error: missing plan during tool execution.", "status": "failure"},
        )
        entry = HistoryEntry(
            plan=plan,
            observation=error_msg,
            status="failure",
            start_time=start_time,
            end_time=time.time(),
            duration_ms=(time.time() - start_time) * 1000,
        )
        return {"history": state.history + [entry], "latest_plan": plan}

    tool_name = plan.tool_name
    tool_args = plan.tool_args
    tool_output: Any
    status: Literal["success", "failure"] = "success"

    logger.info(
        f"Executing tool: `{tool_name}`",
        extra={"event_type": "ToolStart", "tool_name": tool_name, "tool_args": tool_args},
    )

    if tool_name == "finish":
        tool_output = (
            f"Task signaled to finish by agent. Reason: '{tool_args.get('reason', 'No reason given.')}'"
            f". Status: '{tool_args.get('status', 'unknown')}'."
        )
        logger.info(tool_output)
    else:
        try:
            tool_entry = get_tool(tool_name, safe_mode=state.runtime.safe_mode)
            input_model_instance = tool_entry.input_model(**tool_args)
            timeout_duration = state.runtime.tool_timeout or tool_entry.timeout

            if timeout_duration is not None and timeout_duration > 0:
                tool_output = await asyncio.wait_for(
                    _run_tool(tool_entry.run, input_model_instance, state),
                    timeout=timeout_duration,
                )
            else:
                tool_output = await _run_tool(tool_entry.run, input_model_instance, state)

        except (ToolNotFoundError, ValidationError, ToolExecutionError) as e:
            tool_output = f"[ERROR] {type(e).__name__} for '{tool_name}': {e}"
            status = "failure"
            logger.error(tool_output)
        except asyncio.TimeoutError:
            tool_output = f"[ERROR] Tool '{tool_name}' timed out after {timeout_duration} seconds."
            status = "failure"
            logger.error(tool_output)
        except Exception as e:
            logger.exception(f"Unexpected exception for tool '{tool_name}'", exc_info=True)
            tool_output = f"[ERROR] Unexpected error in tool '{tool_name}': {type(e).__name__}: {e}"
            status = "failure"

    observation_str = json.dumps(tool_output, default=str) if isinstance(tool_output, (dict, list)) else str(tool_output)

    if status == "failure":
        logger.error(
            f"Tool `{tool_name}` failed. Observation/Error: {observation_str}",
            extra={"event_type": "ToolEnd", "tool_name": tool_name, "status": "failure", "error_message": observation_str},
        )
    else:
        logger.info(
            f"Tool `{tool_name}` executed successfully.",
            extra={"event_type": "ToolEnd", "tool_name": tool_name, "status": "success", "output_preview": observation_str[:200]},
        )

    end_time = time.time()
    history_entry = HistoryEntry(
        plan=plan,
        observation=observation_str,
        status=status,
        start_time=start_time,
        end_time=end_time,
        duration_ms=(end_time - start_time) * 1000,
    )

    return {"history": state.history + [history_entry]}