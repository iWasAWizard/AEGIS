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
from typing import Dict, Any, Callable, Literal, Optional, Tuple

import httpx
from pydantic import ValidationError

from aegis.agents.task_state import HistoryEntry, TaskState
from aegis.exceptions import (
    ToolExecutionError,
    ToolNotFoundError,
    ConfigurationError,
)
from aegis.registry import get_tool, ToolEntry
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.config import get_config
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.logger import setup_logger
from aegis.utils.replay_logger import log_replay_event

logger = setup_logger(__name__)


async def _run_tool(tool_func: Callable, input_data: Any, state: TaskState) -> Any:
    """Helper to run the tool's function, inspecting its signature."""
    sig = inspect.signature(tool_func)
    params = sig.parameters
    tool_kwargs = {"input_data": input_data}

    if "state" in params:
        tool_kwargs["state"] = state
    if "provider" in params:
        if state.runtime.backend_profile is None:
            raise ConfigurationError(
                "Cannot execute provider-aware tool: backend_profile not set."
            )
        provider = get_provider_for_profile(state.runtime.backend_profile)
        tool_kwargs["provider"] = provider

    final_kwargs = {k: v for k, v in tool_kwargs.items() if k in params}
    if asyncio.iscoroutinefunction(tool_func):
        return await tool_func(**final_kwargs)
    else:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: tool_func(**final_kwargs))


async def _check_guardrails(plan: AgentScratchpad, state: TaskState) -> Optional[str]:
    """Checks the agent's plan against the NeMo Guardrails service if safe_mode is enabled."""
    safe_mode_enabled = (
        state.runtime.safe_mode if state.runtime.safe_mode is not None else True
    )
    if not safe_mode_enabled:
        logger.info("Safe mode is disabled, skipping Guardrails check.")
        return None

    config = get_config()
    guardrails_url = config.get("services", {}).get("guardrails_url")
    if not guardrails_url:
        return None

    logger.info(f"Checking plan with Guardrails at {guardrails_url}")
    try:
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": f"I want to run the tool named '{plan.tool_name}' with arguments '{json.dumps(plan.tool_args)}'",
                }
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(guardrails_url, json=payload, timeout=10)
            response.raise_for_status()
            guardrail_response = response.json()
            bot_message = (
                guardrail_response.get("messages", [{}])[-1].get("content", "").lower()
            )

            if "i'm sorry" in bot_message or "i cannot" in bot_message:
                rejection_reason = f"[BLOCKED by Guardrails] {bot_message.capitalize()}"
                logger.warning(
                    f"Tool '{plan.tool_name}' blocked. Reason: {rejection_reason}"
                )
                return rejection_reason
    except Exception as e:
        logger.error(
            f"Guardrails check failed: {e}. Allowing tool execution (fail-open)."
        )
    return None


async def _run_tool_with_error_handling(
    tool_entry: ToolEntry, plan: AgentScratchpad, state: TaskState
) -> Tuple[str, Literal["success", "failure"]]:
    """Validates input, runs the tool, and handles all common execution errors."""
    try:
        input_model_instance = tool_entry.input_model(**plan.tool_args)
        timeout = state.runtime.tool_timeout or tool_entry.timeout

        if timeout and timeout > 0:
            tool_output = await asyncio.wait_for(
                _run_tool(tool_entry.run, input_model_instance, state), timeout=timeout
            )
        else:
            tool_output = await _run_tool(tool_entry.run, input_model_instance, state)

        observation = (
            json.dumps(tool_output, default=str)
            if isinstance(tool_output, (dict, list))
            else str(tool_output)
        )
        return observation, "success"

    except (ValidationError, ToolExecutionError, ConfigurationError) as e:
        error_msg = f"[ERROR] {type(e).__name__} for '{plan.tool_name}': {e}"
        logger.error(error_msg)
        return error_msg, "failure"
    except asyncio.TimeoutError:
        error_msg = (
            f"[ERROR] Tool '{plan.tool_name}' timed out after {timeout} seconds."
        )
        logger.error(error_msg)
        return error_msg, "failure"
    except Exception as e:
        logger.exception(f"Unexpected exception for tool '{plan.tool_name}'")
        error_msg = (
            f"[ERROR] Unexpected error in '{plan.tool_name}': {type(e).__name__}: {e}"
        )
        return error_msg, "failure"


async def execute_tool(state: TaskState) -> Dict[str, Any]:
    """Orchestrates tool execution including guardrails, running, and history logging."""
    logger.info("🛠️  Step: Execute Tool")
    start_time = time.time()
    plan = state.latest_plan
    current_history = state.history.copy()
    updated_state_dict: Dict[str, Any] = {"history": current_history}

    if not plan:
        error_msg = "[ERROR] Execution failed: No plan found in state."
        history_entry = HistoryEntry(
            plan=AgentScratchpad.model_validate(
                {
                    "thought": "Critical error: No plan.",
                    "tool_name": "finish",
                    "tool_args": {"reason": error_msg, "status": "failure"},
                }
            ),
            observation=error_msg,
            status="failure",
            start_time=start_time,
            end_time=time.time(),
            duration_ms=(time.time() - start_time) * 1000,
        )
        current_history.append(history_entry)
        return updated_state_dict

    # 1. Check with Guardrails
    rejection_reason = await _check_guardrails(plan, state)
    if rejection_reason:
        history_entry = HistoryEntry(
            plan=plan,
            observation=rejection_reason,
            status="failure",
            start_time=start_time,
            end_time=time.time(),
            duration_ms=(time.time() - start_time) * 1000,
        )
        current_history.append(history_entry)
        return updated_state_dict

    logger.info(
        f"Executing tool: `{plan.tool_name}`",
        extra={
            "event_type": "ToolStart",
            "tool_name": plan.tool_name,
            "tool_args": plan.tool_args,
        },
    )

    # 2. Handle special meta-action tools
    if plan.tool_name == "finish":
        observation, status = (
            f"Task signaled to finish. Reason: '{plan.tool_args.get('reason', 'N/A')}'",
            "success",
        )
    elif plan.tool_name == "clear_short_term_memory":
        observation, status = "Short-term memory cleared.", "success"
        updated_state_dict["history"] = []
    elif plan.tool_name == "revise_goal":
        new_goal = plan.tool_args.get("new_goal", "")
        reason = plan.tool_args.get("reason", "No reason provided.")
        observation = f"Goal has been revised. Reason: {reason}. New Goal: {new_goal}"
        status = "success"
        updated_state_dict["task_prompt"] = new_goal
    elif plan.tool_name == "advance_to_next_sub_goal":
        new_index = state.current_sub_goal_index + 1
        if new_index < len(state.sub_goals):
            observation = f"Acknowledged. Advancing to sub-goal {new_index + 1}: '{state.sub_goals[new_index]}'"
            updated_state_dict["current_sub_goal_index"] = new_index
        else:
            observation = "All sub-goals have been completed."
        status = "success"
    else:
        # 3. Execute any other tool
        try:
            tool_entry = get_tool(plan.tool_name)
            observation, status = await _run_tool_with_error_handling(
                tool_entry, plan, state
            )
        except ToolNotFoundError as e:
            observation, status = f"[ERROR] {type(e).__name__}: {e}", "failure"
            logger.error(observation)

    # 4. Log the ground truth for replay
    log_replay_event(
        state.task_id,
        "TOOL_OUTPUT",
        {"observation": observation, "status": status},
    )

    # 5. Log and create history entry
    log_extra = {
        "event_type": "ToolEnd",
        "tool_name": plan.tool_name,
        "status": status,
        "output_preview": observation[:200],
    }
    if status == "failure":
        logger.error(f"Tool `{plan.tool_name}` failed.", extra=log_extra)
    else:
        logger.info(f"Tool `{plan.tool_name}` executed successfully.", extra=log_extra)

    end_time = time.time()
    history_entry = HistoryEntry(
        plan=plan,
        observation=observation,
        status=status,
        start_time=start_time,
        end_time=end_time,
        duration_ms=(end_time - start_time) * 1000,
    )

    updated_state_dict["history"].append(history_entry)

    return updated_state_dict
