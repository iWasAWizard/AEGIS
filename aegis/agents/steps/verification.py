# aegis/agents/steps/verification.py
"""
Agent steps for outcome verification and remediation.

This module provides the logic for the agent to check the result of its
actions and formulate a new plan if the action failed to produce the
desired outcome.
"""
import json
from typing import Dict, Any, Callable, Awaitable

from pydantic import ValidationError

from aegis.agents.steps.execute_tool import _run_tool
from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError, ToolError
from aegis.registry import get_tool
from aegis.utils.logger import setup_logger
from schemas.plan_output import AgentScratchpad

logger = setup_logger(__name__)


async def verify_outcome(state: TaskState) -> str:
    """Verifies the outcome of the last executed tool.

    :param state: The current agent task state.
    :type state: TaskState
    :return: A routing string: 'success' or 'failure'.
    :rtype: str
    """
    logger.info("🔎 Step: Verify Outcome")
    last_plan = state.latest_plan
    last_observation = state.history[-1][1] if state.history else ""

    if isinstance(last_observation, str) and "[ERROR]" in last_observation:
        logger.warning(f"Verification failed due to error in main tool execution: {last_observation}")
        return "failure"

    if not last_plan or not last_plan.verification_tool_name:
        logger.info("No verification step specified. Assuming success.")
        return "success"

    v_tool_name = last_plan.verification_tool_name
    v_tool_args = last_plan.verification_tool_args or {}
    logger.info(f"Running verification tool: {v_tool_name} with args: {v_tool_args}")

    try:
        tool_entry = get_tool(v_tool_name, safe_mode=state.runtime.safe_mode)
        input_model = tool_entry.input_model(**v_tool_args)
        verification_output = await _run_tool(tool_entry.run, input_model)
    except ToolError as e:
        logger.error(f"Verification tool '{v_tool_name}' failed to execute: {e}")
        return "failure"

    success_keywords = ["running", "active", "exists", "open", "success", "found"]
    output_lower = str(verification_output).lower()
    if any(keyword in output_lower for keyword in success_keywords):
        logger.info(f"Verification successful. Output: '{output_lower[:100]}...'")
        return "success"
    else:
        logger.warning(f"Verification failed. Output did not contain success keywords: '{output_lower[:100]}...'")
        return "failure"


async def remediate_plan(
        state: TaskState, llm_query_func: Callable[[str, str], Awaitable[str]]
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
    last_plan, last_observation = state.history[-1]

    remediation_context = (
        f"Your previous attempt to achieve the goal failed.\n"
        f"Main Goal: {state.task_prompt}\n"
        f"Action Attempted: You ran the tool `{last_plan.tool_name}` with arguments `{json.dumps(last_plan.tool_args)}`.\n"
        f"Observed Outcome: {last_observation}\n\n"
        f"This outcome was not successful. Analyze the observed outcome and your previous thought process. "
        f"Formulate a new plan to either fix the problem or try an alternative approach to achieve the original goal. "
        f"If you are stuck, consider using `query_knowledge_base` to find solutions."
    )
    from aegis.agents.steps.reflect_and_plan import construct_planning_prompt
    system_prompt, _ = construct_planning_prompt(state)
    user_prompt = remediation_context + "\n\n## Your New JSON Response:"

    try:
        llm_response_str = await llm_query_func(system_prompt, user_prompt)
        parsed_json = json.loads(llm_response_str)
        scratchpad = AgentScratchpad.model_validate(parsed_json)
        logger.info(f"✅ Remediation plan generated: Calling tool `{scratchpad.tool_name}`")
        return {"latest_plan": scratchpad}
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse or validate LLM remediation plan. Error: {e}")
        raise PlannerError(f"LLM returned malformed remediation plan. Error: {e}") from e
