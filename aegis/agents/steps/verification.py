# aegis/agents/steps/verification.py
"""
Agent steps for outcome verification and remediation.

This module provides the logic for the agent to check the result of its
actions and formulate a new plan if the action failed to produce the
desired outcome.
"""
import json
from typing import Dict, Any, Callable, Awaitable, Literal

from pydantic import ValidationError

from aegis.agents.steps.check_termination import check_termination
from aegis.agents.steps.execute_tool import _run_tool
from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError
from aegis.registry import get_tool
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


async def verify_outcome(
    state: TaskState, llm_query_func: Callable[..., Awaitable[str]]
) -> Dict[str, Any]:
    """
    Verifies the outcome of the last executed tool using an LLM call for judgment.
    """
    logger.info("🔎 Step: Verify Outcome (LLM-driven)")
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
        tool_entry = get_tool(
            v_tool_name,
            safe_mode=(
                state.runtime.safe_mode
                if state.runtime.safe_mode is not None
                else False
            ),
        )
        input_model = tool_entry.input_model(**v_tool_args)
        verification_output = await _run_tool(tool_entry.run, input_model, state)
    except Exception as e:
        logger.error(f"Verification tool '{v_tool_name}' failed to execute: {e}")
        last_history_entry.verification_status = "failure"
        return {"history": state.history}

    system_prompt = (
        "You are a verification system. Your task is to determine if an action was successful. "
        "Based on the plan, the action's result, and a verification step's output, "
        "you must respond with only one word: 'success' or 'failure'."
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
        f"Respond with only 'success' or 'failure'."
    )

    try:
        response = await llm_query_func(system_prompt, user_prompt, state.runtime)
        result = response.strip().lower()
        if result not in ["success", "failure"]:
            logger.warning(
                f"LLM verifier gave ambiguous response: '{response}'. Defaulting to failure."
            )
            result = "failure"
        # Cast result to Literal['success', 'failure']
        if result == "success":
            last_history_entry.verification_status = "success"
        elif result == "failure":
            last_history_entry.verification_status = "failure"
        else:
            last_history_entry.verification_status = None
        logger.info(f"LLM verification result: '{result}'")
    except Exception as e:
        logger.error(f"LLM call for verification failed: {e}. Defaulting to failure.")
        last_history_entry.verification_status = "failure"

    return {"history": state.history}


def route_after_verification(state: TaskState) -> str:
    """
    Routes the agent based on the verification status of the last step.
    This acts as a conditional edge logic function.

    :param state: The current agent task state.
    :type state: TaskState
    :return: A routing string: "remediate_plan", "continue", or "end".
    :rtype: str
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


async def remediate_plan(
    state: TaskState, llm_query_func: Callable[..., Awaitable[str]]
) -> Dict[str, Any]:
    """Asks the LLM to create a new plan to recover from a failed step.

    :param state: The current agent task state.
    :type state: TaskState
    :param llm_query_func: The async function to call for LLM queries.
    :type llm_query_func: Callable
    :return: A dictionary with the new `latest_plan`.
    :rtype: Dict[str, Any]
    :raises PlannerError: If the LLM response for remediation is unparsable.
    """
    logger.info("🩹 Step: Remediate Plan")
    last_history_entry = state.history[-1]
    last_plan = last_history_entry.plan
    last_observation = last_history_entry.observation

    remediation_context = (
        f"Your previous attempt to achieve the goal failed. Here is the context:\n\n"
        f"**Main Goal:** {state.task_prompt}\n\n"
        f"**Failed Step Details:**\n"
        f"- **Your Thought:** {last_plan.thought}\n"
        f"- **Action Attempted:** You ran the tool `{last_plan.tool_name}` with arguments `{json.dumps(last_plan.tool_args, default=str)}`.\n"
        f"- **Observed Outcome (The Error):** {last_observation}\n\n"
        f"**Your Task:**\n"
        f"Analyze the error in the 'Observed Outcome'. The plan was flawed. "
        f"Formulate a new, single-step plan to either fix the problem directly or to try a different approach to achieve the original goal. "
        f"If you are stuck, consider using `query_knowledge_base` to find solutions from past tasks. "
        f"Create a new JSON object with your corrected plan."
    )
    # Import locally to avoid circular dependency issues at module load time
    from aegis.agents.steps.reflect_and_plan import construct_planning_prompt

    system_prompt, _ = construct_planning_prompt(state)
    user_prompt = remediation_context

    try:
        llm_response_str = await llm_query_func(
            system_prompt,
            user_prompt,
            runtime_config=state.runtime,
        )
        parsed_json = json.loads(llm_response_str)
        scratchpad = AgentScratchpad.model_validate(parsed_json)
        logger.info(
            f"✅ Remediation plan generated: Calling tool `{scratchpad.tool_name}`"
        )
        return {"latest_plan": scratchpad}
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse or validate LLM remediation plan. Error: {e}")
        raise PlannerError(
            f"LLM returned malformed remediation plan. Error: {e}"
        ) from e
