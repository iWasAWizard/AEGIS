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
import dataclasses
import os
import hashlib

import httpx
from aegis.utils.policy import authorize, simulate as policy_simulate
from aegis.utils.dryrun import dry_run
from aegis.schemas.tool_result import ToolResult  # available for tool wrappers
from pydantic import ValidationError, BaseModel

from aegis.agents.task_state import HistoryEntry, TaskState
from aegis.exceptions import (
    ConfigurationError,
    ToolExecutionError,
    ToolNotFoundError,
)
from aegis.registry import get_tool, ToolEntry
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.config import get_config
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.logger import setup_logger
from aegis.utils.replay_logger import log_replay_event
from aegis.utils import provenance
from aegis.utils.redact import redact_for_log  # NEW: log redaction

# NEW: artifacts for oversized outputs
from aegis.utils import artifacts as art

logger = setup_logger(__name__)


def _max_stdio_bytes() -> int:
    try:
        return int(os.environ.get("AEGIS_MAX_STDIO_BYTES", "1048576"))
    except Exception:
        return 1048576


def _schema_hash(model_cls) -> str:
    try:
        schema = model_cls.model_json_schema()
        blob = json.dumps(schema, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
    except Exception:
        return "unknown"


def _redaction_hash(payload: Dict[str, Any]) -> str:
    try:
        red = redact_for_log(payload)
        blob = json.dumps(red, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
    except Exception:
        try:
            blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            return hashlib.sha256(blob).hexdigest()
        except Exception:
            return "unknown"


def _store_observation_artifact(
    *,
    run_id: Optional[str],
    tool_name: str,
    name: str,
    data: bytes,
) -> Optional[art.ArtifactRef]:
    return art.write_blob(
        run_id=run_id,
        tool_name=tool_name,
        preferred_name=name,
        data=data,
        subdir=None,
    )


def _truncate_text_with_artifact(
    *,
    run_id: Optional[str],
    tool_name: str,
    field_name: str,
    text: Optional[str],
    max_bytes: int,
) -> Tuple[Optional[str], bool, Optional[art.ArtifactRef]]:
    """
    For arbitrary text (observation fallback), truncate and artifact if needed.
    Returns (possibly-truncated-text, truncated_flag, artifact_ref|None)
    """
    if text is None:
        return None, False, None
    data = text.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return text, False, None
    ref = _store_observation_artifact(
        run_id=run_id,
        tool_name=tool_name,
        name=f"{field_name}.txt",
        data=data,
    )
    head = data[:max_bytes]
    return head.decode("utf-8", errors="replace"), True, ref


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
    if "config" in params:
        tool_kwargs["config"] = get_config()

    # Execute tool function (async or sync)
    if inspect.iscoroutinefunction(tool_func):
        return await tool_func(**tool_kwargs)
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: tool_func(**tool_kwargs))


async def _check_guardrails(plan: AgentScratchpad, state: TaskState) -> Optional[str]:
    """
    If configured, call an external Guardrails endpoint to preflight the tool call.
    Return a human-readable rejection reason if blocked; otherwise None.
    """
    try:
        guardrails_url = state.runtime.guardrails_url
        if not guardrails_url:
            return None

        payload = {
            "messages": [
                {"role": "user", "content": state.task_prompt},
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "thought": plan.thought,
                            "tool_name": plan.tool_name,
                            "tool_args": plan.tool_args,
                        }
                    ),
                },
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


def _degenerate_repeat(
    history: list[HistoryEntry], tool_name: str, tool_args: Dict[str, Any], k: int = 3
) -> bool:
    """
    Return True if the last (k-1) history entries are failures whose `plan.tool_name`
    and `plan.tool_args` exactly match the current request. This prevents tight loops
    repeatedly invoking the same failing action.
    """
    if k <= 1:
        return False
    if not history:
        return False

    recent = list(reversed(history))[: k - 1]
    for h in recent:
        try:
            if h.status != "failure":
                return False
            if getattr(h, "plan", None) is None:
                return False
            if h.plan.tool_name != tool_name:
                return False
            if (h.plan.tool_args or {}) != (tool_args or {}):
                return False
        except Exception:
            return False
    return len(recent) == (k - 1)


async def _run_tool_with_error_handling(
    tool_entry: ToolEntry, plan: AgentScratchpad, state: TaskState
) -> Tuple[str, Literal["success", "failure"]]:
    """Validates input, runs the tool, and handles all common execution errors."""
    try:
        input_model_instance = tool_entry.input_model(**plan.tool_args)
    except ValidationError as e:
        return f"[ERROR] Invalid input for '{plan.tool_name}': {e}", "failure"

    timeout = tool_entry.timeout or state.runtime.tool_timeout

    try:
        tool_output = await asyncio.wait_for(
            _run_tool(tool_entry.func, input_model_instance, state), timeout=timeout
        )

        # === Provenance & Guardrails for ToolResult ===
        if isinstance(tool_output, ToolResult):
            try:
                # Enrich provenance on the ToolResult itself
                schema_h = _schema_hash(tool_entry.input_model)
                red_h = _redaction_hash(plan.tool_args)
                machine_id = None
                for key in ("machine_id", "machineId", "host_id"):
                    if key in (plan.tool_args or {}) and isinstance(
                        plan.tool_args[key], str
                    ):
                        machine_id = plan.tool_args[key]
                        break
                tool_output.enrich_provenance(
                    tool_name=plan.tool_name,
                    run_id=state.task_id,
                    args_schema_hash=schema_h,
                    redaction_hash=red_h,
                    machine_id=machine_id,
                )

                # Attach artifacts & truncate large stdout/stderr
                tool_output.attach_artifacts_and_truncate(
                    tool_name=plan.tool_name,
                    run_id=state.task_id,
                    max_stdio_bytes=_max_stdio_bytes(),
                    store_fn=lambda preferred_name, data: art.write_blob(
                        run_id=state.task_id,
                        tool_name=plan.tool_name,
                        preferred_name=preferred_name,
                        data=data,
                        subdir=None,
                    ),
                )
            except Exception as enrich_err:
                logger.error(f"Provenance/guardrail enrichment failed: {enrich_err}")

        # === Normalization (avoid repr/ellipses): serialize models & dataclasses ===
        payload = None
        if isinstance(tool_output, BaseModel):
            try:
                payload = tool_output.model_dump()
            except Exception:
                payload = json.loads(tool_output.model_dump_json())
        elif dataclasses.is_dataclass(tool_output):
            try:
                payload = dataclasses.asdict(tool_output)
            except Exception:
                payload = tool_output
        elif isinstance(tool_output, (dict, list)):
            payload = tool_output
        else:
            payload = tool_output

        # Convert payload to observation string
        if isinstance(payload, (dict, list)):
            obs_text = json.dumps(payload, ensure_ascii=False, indent=2)
        else:
            obs_text = str(payload)

        # FINAL guardrail for observation size (for non-ToolResult or adapter raw strings)
        if not isinstance(tool_output, ToolResult):
            try:
                obs_text, truncated, _ = _truncate_text_with_artifact(
                    run_id=state.task_id,
                    tool_name=plan.tool_name,
                    field_name="observation",
                    text=obs_text,
                    max_bytes=_max_stdio_bytes(),
                )
                if truncated:
                    logger.info(
                        f"Observation truncated for tool '{plan.tool_name}' (see artifact)."
                    )
            except Exception as trunc_err:
                logger.error(f"Observation truncation failed: {trunc_err}")

        return obs_text, "success"

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

    updated_state_dict: Dict[str, Any] = {"history": state.history.copy()}
    current_history = updated_state_dict["history"]

    # 0. Extract latest plan
    if not state.plans:
        error_msg = "No plan to execute."
        logger.error(error_msg)
        history_entry = HistoryEntry(
            plan=AgentScratchpad(thought="N/A", tool_name="N/A", tool_args={}),
            observation=error_msg,
            status="failure",
            start_time=time.time(),
            end_time=time.time(),
            duration_ms=0,
        )
        current_history.append(history_entry)
        return updated_state_dict

    plan = state.plans[-1]
    start_time = time.time()

    # 0b. Degeneracy guard
    try:
        if _degenerate_repeat(current_history, plan.tool_name, plan.tool_args, k=3):
            observation = "[DEGENERACY GUARD] Repeated failures with identical tool and args detected; halting this action to prevent a loop."
            history_entry = HistoryEntry(
                plan=plan,
                observation=observation,
                status="failure",
                start_time=start_time,
                end_time=time.time(),
                duration_ms=(time.time() - start_time) * 1000,
            )
            current_history.append(history_entry)
            return updated_state_dict
    except Exception as dg_err:
        logger.error(f"Degeneracy guard check failed: {dg_err}. Continuing.")

    # 1. Guardrails
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

    # 1b. Policy authorization
    try:
        _args = plan.tool_args or {}
        target_host = (
            _args.get("target")
            or _args.get("host")
            or _args.get("ip")
            or _args.get("address")
        )
        interface = _args.get("interface") or _args.get("iface") or _args.get("nic")
        decision = authorize(
            actor="agent",
            tool=plan.tool_name,
            target_host=target_host,
            interface=interface,
            args=_args,
        )
        if decision.effect == "DENY":
            observation = f"[POLICY DENIED] {decision.reason}"
            status = "failure"
            log_replay_event(
                state.task_id,
                "POLICY_DENY",
                {
                    "tool": plan.tool_name,
                    "reason": decision.reason,
                    "meta": decision.metadata,
                },
            )
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
            # provenance record
            try:
                provenance.record_step(
                    run_id=state.task_id,
                    step_index=len(updated_state_dict["history"]) - 1,
                    tool=plan.tool_name,
                    tool_args=plan.tool_args,
                    target_host=target_host,
                    interface=interface,
                    status=status,
                    observation=observation,
                    duration_ms=int((end_time - start_time) * 1000),
                )
            except Exception:
                pass
            return updated_state_dict
        elif decision.effect == "REQUIRE_APPROVAL":
            observation = f"[APPROVAL REQUIRED] {decision.reason}"
            status = "failure"
            log_replay_event(
                state.task_id,
                "POLICY_REQUIRE_APPROVAL",
                {
                    "tool": plan.tool_name,
                    "reason": decision.reason,
                    "meta": decision.metadata,
                },
            )
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
            try:
                provenance.record_step(
                    run_id=state.task_id,
                    step_index=len(updated_state_dict["history"]) - 1,
                    tool=plan.tool_name,
                    tool_args=plan.tool_args,
                    target_host=target_host,
                    interface=interface,
                    status=status,
                    observation=observation,
                    duration_ms=int((end_time - start_time) * 1000),
                )
            except Exception:
                pass
            return updated_state_dict
    except Exception as _e:
        logger.error(f"Policy check error: {_e}. Failing open (allowing).")

    # 2. Log tool start (with redacted args only in logs)
    logger.info(
        f"Executing tool: `{plan.tool_name}`",
        extra={
            "event_type": "ToolStart",
            "tool_name": plan.tool_name,
            "tool_args": redact_for_log(plan.tool_args),  # REDACTED for logs
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
        # 3. Execute ordinary tool via registry
        try:
            tool_entry = get_tool(plan.tool_name)

            # 3a. Dry-run short-circuit: preview without executing
            if dry_run.enabled:
                preview = {
                    "tool": plan.tool_name,
                    "args": plan.tool_args,
                    "mode": "dry-run",
                }
                observation, status = (
                    f"[DRY-RUN] would execute {plan.tool_name} with args {json.dumps(plan.tool_args)}",
                    "success",
                )
            else:
                observation, status = await _run_tool_with_error_handling(
                    tool_entry, plan, state
                )
        except ToolNotFoundError as e:
            observation, status = f"[ERROR] {type(e).__name__}: {e}", "failure"
            logger.error(observation)

    # 4. Log the ground truth for replay (keep as-is; replay is internal)
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
    }
    # If you later add observation to logs, pass redact_for_log(observation) instead.
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

    # 6. Provenance record (full fidelity; no redaction here)
    try:
        _args = plan.tool_args or {}
        target_host = (
            _args.get("target")
            or _args.get("host")
            or _args.get("ip")
            or _args.get("address")
        )
        interface = _args.get("interface") or _args.get("iface") or _args.get("nic")
        provenance.record_step(
            run_id=state.task_id,
            step_index=len(updated_state_dict["history"]) - 1,
            tool=plan.tool_name,
            tool_args=plan.tool_args,
            target_host=target_host,
            interface=interface,
            status=status,
            observation=observation,
            duration_ms=int((end_time - start_time) * 1000),
        )
    except Exception:
        pass

    return updated_state_dict
