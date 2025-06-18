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
from aegis.exceptions import PlannerError, ToolError
from aegis.registry import get_tool
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


async def verify_outcome(state: TaskState) -> Dict[str, Any]:
    """
    Verifies the outcome of the last executed tool and updates the history with the result.

    This function is a standard graph node. It runs the verification logic and
    updates the `verification_status` in the last history entry. It returns a
    dictionary with the updated history to merge back into the main state.

    :param state: The current agent task state.
    :type state: TaskState
    :return: A dictionary containing the updated history list.
    :rtype: Dict[str, Any]
    """
    logger.info("🔎 Step: Verify Outcome")
    logger.debug(f"Entering verify_outcome with state: {repr(state)}")

    if not state.history:
        logger.warning(
            "Verification called with no history. This should not happen in a valid graph."
        )
        return state.model_dump()

    last_history_entry = state.history[-1]
    last_observation = last_history_entry.observation
    last_plan = state.latest_plan

    # Default to success if no verification is planned
    verification_result: Literal["success", "failure"] = "success"

    if last_history_entry.status == "failure":
        logger.warning(
            f"Verification automatically failed due to error in main tool execution: {last_observation}"
        )
        verification_result = "failure"
    elif last_plan and last_plan.verification_tool_name:
        v_tool_name = last_plan.verification_tool_name
        v_tool_args = last_plan.verification_tool_args or {}
        logger.info(
            f"Running verification tool: {v_tool_name} with args: {v_tool_args}"
        )

        try:
            tool_entry = get_tool(v_tool_name, safe_mode=state.runtime.safe_mode)
            input_model = tool_entry.input_model(**v_tool_args)
            verification_output = await _run_tool(tool_entry.run, input_model)

            success_keywords = [
                "running",
                "active",
                "exists",
                "open",
                "success",
                "found",
            ]
            output_lower = str(verification_output).lower()

            if any(keyword in output_lower for keyword in success_keywords):
                logger.info(
                    f"Verification successful. Output: '{output_lower[:100]}...'"
                )
                verification_result = "success"
            else:
                logger.warning(
                    f"Verification failed. Output did not contain success keywords: '{output_lower[:100]}...'"
                )
                verification_result = "failure"

        except ToolError as e:
            logger.error(f"Verification tool '{v_tool_name}' failed to execute: {e}")
            verification_result = "failure"

    last_history_entry.verification_status = verification_result
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
        return "remediate_plan"  # Should not happen if graph is well-formed

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
    logger.debug(f"Entering remediate_plan with state: {repr(state)}")

    last_history_entry = state.history[-1]
    last_plan = last_history_entry.plan
    last_observation = last_history_entry.observation

    remediation_context = (
        f"Your previous attempt to achieve the goal failed.\n"
        f"Main Goal: {state.task_prompt}\n"
        f"Action Attempted: You ran the tool `{last_plan.tool_name}` "
        f"with arguments `{json.dumps(last_plan.tool_args, default=str)}`.\n"
        f"Observed Outcome: {last_observation}\n\n"
        f"This outcome was not successful. Analyze the observed outcome and your previous thought process. "
        f"Formulate a new plan to either fix the problem or try an alternative approach to achieve the original goal. "
        f"If you are stuck, consider using `query_knowledge_base` to find solutions."
    )
    # Import locally to avoid circular dependency issues at module load time
    from aegis.agents.steps.reflect_and_plan import construct_planning_prompt

    system_prompt, _ = construct_planning_prompt(state)
    user_prompt = remediation_context + "\n\n## Your New JSON Response:"

    try:
        llm_response_str = await llm_query_func(
            system_prompt,
            user_prompt,
            runtime_config=state.runtime,  # Pass the whole runtime_config
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
