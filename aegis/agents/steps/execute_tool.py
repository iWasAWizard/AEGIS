# aegis/agents/steps/execute_tool.py
"""
The core tool execution step for the agent.

This module contains the `execute_tool` function, which is responsible for
looking up a tool in the registry, validating its arguments, running it, and
recording the results in a structured history entry.
"""

import asyncio
import json
import time
from typing import Dict, Any, Callable, Literal

from pydantic import ValidationError

from aegis.agents.task_state import HistoryEntry, TaskState
from aegis.exceptions import ToolExecutionError, ToolNotFoundError
from aegis.registry import get_tool
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.logger import setup_logger

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
    logger.info("🛠️  Step: Execute Tool")
    logger.debug(f"Entering execute_tool with state: {repr(state)}")
    start_time = time.time()
    plan = state.latest_plan

    if not plan:
        error_msg = "[ERROR] Execution failed: No plan found in state."
        logger.error(
            error_msg, extra={"event_type": "InternalError", "reason": "Missing plan"}
        )
        # Create a plan to finish with failure if no plan exists
        plan = AgentScratchpad(
            thought="Critical error: No plan was provided to the executor step. Terminating task.",
            tool_name="finish",
            tool_args={
                "reason": "Internal error: missing plan during tool execution.",
                "status": "failure",
            },
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
        extra={
            "event_type": "ToolStart",
            "tool_name": tool_name,
            "tool_args": tool_args,
        },
    )

    if tool_name == "finish":
        tool_output = (
            f"Task signaled to finish by agent. Reason: '{tool_args.get('reason', 'No reason given.')}'"
            f". Status: '{tool_args.get('status', 'unknown')}'."
        )
        logger.info(tool_output)
    else:
        try:
            logger.debug(
                f"Attempting to get tool: '{tool_name}' with safe_mode: {state.runtime.safe_mode}"
            )
            tool_entry = get_tool(tool_name, safe_mode=state.runtime.safe_mode)
            logger.debug(
                f"Tool entry found for '{tool_name}'. Input model: {tool_entry.input_model.__name__}"
            )

            logger.debug(
                f"Attempting to validate input_model for '{tool_name}' with args: {tool_args}"
            )
            input_model_instance = tool_entry.input_model(**tool_args)
            logger.debug(f"Input model for '{tool_name}' validated successfully.")

            timeout_duration = state.runtime.tool_timeout
            if timeout_duration is None and tool_entry.timeout is not None:
                timeout_duration = tool_entry.timeout

            logger.debug(
                f"Preparing to run tool '{tool_name}' via _run_tool. Timeout duration: {timeout_duration}s"
            )
            if timeout_duration is not None and timeout_duration <= 0:
                logger.warning(
                    f"Timeout for tool '{tool_name}' is non-positive ({timeout_duration}s). "
                    f"Running without asyncio.wait_for timeout."
                )
                timeout_duration = None

            if timeout_duration:
                tool_output = await asyncio.wait_for(
                    _run_tool(tool_entry.run, input_model_instance),
                    timeout=timeout_duration,
                )
            else:
                tool_output = await _run_tool(tool_entry.run, input_model_instance)
            logger.debug(
                f"Tool '{tool_name}' _run_tool completed. Output type: {type(tool_output)}"
            )

        except ToolNotFoundError as e:
            tool_output = f"[ERROR] Tool lookup failed for '{tool_name}': {e}"
            status = "failure"
            logger.error(f"ToolNotFoundError for '{tool_name}': {e}")
        except ValidationError as e:
            tool_output = f"[ERROR] Input validation failed for tool '{tool_name}': {e}"
            status = "failure"
            logger.error(
                f"ValidationError for '{tool_name}' with args {tool_args}: {e}"
            )
        except asyncio.TimeoutError:
            effective_timeout_for_log = (
                timeout_duration or "N/A (no timeout set for wait_for)"
            )
            tool_output = f"[ERROR] Tool '{tool_name}' timed out after {effective_timeout_for_log} seconds."
            status = "failure"
            logger.error(tool_output)
        except Exception as e:
            logger.exception(
                f"Unexpected generic exception caught in execute_tool for tool '{tool_name}' with args {tool_args}. "
                f"Original error type: {type(e).__name__}, message: {e}",
                exc_info=True,
            )
            wrapped_error = ToolExecutionError(
                f"Tool '{tool_name}' failed during execution. ErrorType: {type(e).__name__}, Message: {str(e)}"
            )
            tool_output = f"[ERROR] {wrapped_error}"
            status = "failure"

    # Ensure tool_output (which becomes observation) is stringified for consistent history logging
    if not isinstance(tool_output, str):
        try:
            if isinstance(tool_output, (dict, list)):
                observation_str = json.dumps(tool_output, indent=2, default=str)
            else:
                observation_str = str(tool_output)
        except Exception as serialization_exception:
            observation_str = (
                f"[OBSERVATION SERIALIZATION ERROR] Could not serialize tool output of type "
                f"{type(tool_output).__name__}. Error: {serialization_exception}"
            )
            logger.error(
                f"Failed to serialize tool_output for {tool_name} of type {type(tool_output)}. "
                f"Original: {repr(tool_output)[:200]}"
            )
    else:
        observation_str = tool_output

    if status == "failure":
        logger.error(
            f"Tool `{tool_name}` failed. Observation/Error: {observation_str}",
            extra={
                "event_type": "ToolEnd",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "status": "failure",
                "error_message": observation_str,
            },
        )
    else:
        logger.info(
            f"Tool `{tool_name}` executed successfully.",
            extra={
                "event_type": "ToolEnd",
                "tool_name": tool_name,
                "status": "success",
                "output_preview": observation_str[:200]
                + ("..." if len(observation_str) > 200 else ""),
            },
        )

    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000

    history_entry = HistoryEntry(
        plan=plan,
        observation=observation_str,
        status=status,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
    )

    new_history = state.history + [history_entry]
    logger.debug(
        f"Exiting execute_tool. New history length: {len(new_history)}. Last entry status: {status}"
    )
    return {"history": new_history}
