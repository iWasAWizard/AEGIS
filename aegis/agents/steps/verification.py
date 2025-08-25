# aegis/agents/steps/verification.py
import json
from typing import Dict, Any, Callable, Awaitable, Literal, List, cast

from pydantic import BaseModel, Field, ValidationError

from aegis.agents.steps.check_termination import check_termination
from aegis.agents.steps.execute_tool import _run_tool
from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError, ConfigurationError
from aegis.registry import get_tool
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.logger import setup_logger
from aegis.utils.tracing import span
from aegis.utils.replay_logger import log_replay_event


logger = setup_logger(__name__)


class VerificationJudgement(BaseModel):
    """Schema for the LLM's verification decision."""

    judgement: Literal["success", "failure"] = Field(
        ...,
        description="Your judgement on whether the action was successful based on the verification step.",
    )


async def verify_outcome(state: TaskState) -> Dict[str, Any]:
    """
    Verifies the outcome of the last executed tool using a structured LLM call.
    """
    logger.info("🔎 Step: Verify Outcome")
    last_history_entry = state.history[-1]
    last_observation = last_history_entry.observation
    last_plan = state.latest_plan

    if last_history_entry.status == "failure":
        logger.warning(
            f"Verification automatically failed due to error in main tool: {last_observation}"
        )
        last_history_entry.verification_status = "failure"
        return {"history": state.history}

    if not last_plan or not last_plan.verification_tool_name:
        logger.info("No verification tool specified in plan. Assuming success.")
        last_history_entry.verification_status = "success"
        return {"history": state.history}

    v_tool_name = last_plan.verification_tool_name
    v_tool_args = last_plan.verification_tool_args or {}
    logger.info(f"Running verification tool: {v_tool_name} with args: {v_tool_args}")

    try:
        tool_entry = get_tool(v_tool_name, safe_mode=bool(state.runtime.safe_mode))
        input_model = tool_entry.input_model(**v_tool_args)
        verification_output = await _run_tool(tool_entry.run, input_model, state)
    except Exception as e:
        logger.error(f"Verification tool '{v_tool_name}' failed to execute: {e}")
        last_history_entry.verification_status = "failure"
        return {"history": state.history}

    system_prompt = (
        "You are a verification system. Your task is to determine if an action was successful. "
        "Based on the plan, the action's result, and a verification step's output, "
        "you must respond with a JSON object containing your judgement."
    )
    user_prompt = (
        f"## Original Plan\n"
        f"**Thought:** {last_plan.thought}\n"
        f"**Action:** Ran tool `{last_plan.tool_name}` with args `{json.dumps(last_plan.tool_args)}`.\n\n"
        f"## Result of Action\n"
        f"```\n{last_observation}\n```\n\n"
        f"## Verification Step\n"
        f"To confirm the result, the tool `{v_tool_name}` was run. Its output was:\n"
        f"```\n{verification_output}\n```\n\n"
        f"## Your Judgement\n"
        f"Did the original action achieve its goal, as confirmed by the verification step? "
        f"Provide your judgement in the required JSON format."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        if not state.runtime.backend_profile:
            raise ConfigurationError("Backend profile is not set in task state.")

        provider = get_provider_for_profile(state.runtime.backend_profile)
        with span(
            "verifier.judge",  # standardized span name
            run_id=state.task_id,
            tool=(
                getattr(last_history_entry.plan, "tool_name", None)
                if hasattr(last_history_entry, "plan")
                else None
            ),
        ):
            response = await provider.get_structured_completion(
                messages=messages,
                response_model=VerificationJudgement,
                runtime_config=state.runtime,
            )
        judgement = cast(VerificationJudgement, response)
        last_history_entry.verification_status = judgement.judgement
        logger.info(f"LLM verification result: '{judgement.judgement}'")

    except Exception as e:
        logger.error(f"LLM call for verification failed: {e}. Defaulting to failure.")
        last_history_entry.verification_status = "failure"

    return {"history": state.history}


def route_after_verification(state: TaskState) -> str:
    """
    Routes the agent based on the verification status of the last step.
    This acts as a conditional edge logic function.
    """
    logger.info("🚦 Step: Route After Verification")
    if not state.history:
        return "remediate_plan"

    last_verification_status = state.history[-1].verification_status
    logger.debug(f"Routing based on verification status: '{last_verification_status}'")

    if last_verification_status == "failure":
        return "remediate_plan"
    else:
        # If verification passed, we then check if the overall task is finished.
        return check_termination(state)


async def remediate_plan(state: TaskState) -> Dict[str, Any]:
    """Asks the LLM to create a new, validated plan to recover from a failed step."""
    logger.info("🩹 Step: Remediate Plan")
    # This reuses the main planning logic, but with a special prompt
    from aegis.agents.steps.reflect_and_plan import (
        reflect_and_plan,
        construct_planning_messages,
        _select_relevant_tools,
    )

    last_history_entry = state.history[-1]

    # Create a new state object with a modified prompt for remediation
    remediation_prompt = (
        f"The previous step failed. Analyze the last observation and create a new plan to recover and achieve the original goal.\n"
        f"Original Goal: {state.task_prompt}"
    )
    remediation_state = state.model_copy()
    remediation_state.task_prompt = remediation_prompt

    # We can reuse the main reflect_and_plan logic by passing it this modified state
    return await reflect_and_plan(remediation_state)
