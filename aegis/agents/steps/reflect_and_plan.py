# aegis/agents/steps/reflect_and_plan.py
"""
The core planning step for the agent.

This module contains the `reflect_and_plan` function, which is responsible
for a single "thought" cycle of the agent. It analyzes the task, reviews the
history, and uses the LLM to decide on the next action to take.
"""

import json
from typing import Dict, Any, List, Callable, Awaitable

from pydantic import ValidationError

from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError
from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger
from schemas.plan_output import AgentScratchpad

logger = setup_logger(__name__)


def get_tool_schemas() -> str:
    # ... (function content is unchanged)
    tool_signatures: List[str] = []
    excluded_tags = {"internal"}
    for tool_name, tool_entry in sorted(TOOL_REGISTRY.items()):
        if any(tag in tool_entry.tags for tag in excluded_tags) and tool_name != "query_knowledge_base":
            continue
        try:
            schema = tool_entry.input_model.model_json_schema()
            properties = schema.get("properties", {})
            required_args = set(schema.get("required", []))
            arg_parts = []
            for name, details in properties.items():
                arg_type = details.get("type", "any")
                part = f"{name}: {arg_type}"
                if name not in required_args:
                    part += " (optional)"
                arg_parts.append(part)
            args_signature = ", ".join(arg_parts)
            full_signature = f"- {tool_name}({args_signature}): {tool_entry.description}"
            tool_signatures.append(full_signature)
        except Exception as e:
            logger.warning(f"Could not generate signature for tool '{tool_name}': {e}")
    finish_desc = "Call this to signal that the task is complete. Provide a summary of the outcome."
    tool_signatures.append(f"- finish(reason: string, status: string): {finish_desc}")
    return "\n".join(tool_signatures)


def construct_planning_prompt(state: TaskState) -> tuple[str, str]:
    """Constructs the full system and user prompts for the LLM planner."""
    history_str = ""
    if not state.history:
        history_str = "This is the first step. Begin by thinking about the user's request."
    else:
        for i, entry in enumerate(state.history):
            history_str += (
                f"### Step {i + 1}:\n"
                f"**Thought:** {entry.plan.thought}\n"
                f"**Action:** Called tool `{entry.plan.tool_name}` "
                f"with args `{json.dumps(entry.plan.tool_args)}`.\n"
                f"**Observation:** `{str(entry.observation)}`\n\n"
            )

    # ... (system_prompt and user_prompt construction remains the same)
    system_prompt = (
        "You are AEGIS, an autonomous agent. Your goal is to complete the user's task by thinking "
        "step-by-step and using the available tools.\n\n"
        "## Instructions\n"
        "1.  **Analyze the Goal & History:** Review the user's goal and what you've already done.\n"
        "2.  **Think:** In the `thought` field, reason about the next logical step.\n"
        "3.  **Choose ONE Tool:** Select a single tool for the main action in this step.\n"
        "4.  **Plan Verification (Optional but Recommended):** After choosing a tool, think about how to check if it worked. "
        "For example, if you start a service, you should check its status. If you create a file, you should check if it exists. "
        "Provide this check in the `verification_tool_name` and `verification_tool_args` fields.\n"
        "5.  **Finish:** If the task is complete, you MUST use the `finish` tool.\n"
        "6.  **Respond ONLY with a valid JSON object.** Do not add any text before or after the JSON.\n\n"
        "## Available Tools\n"
        f"{get_tool_schemas()}\n\n"
        "## Response Format\n"
        "You must respond with a single JSON object. The `verification` fields are optional but highly encouraged.\n"
        "{\n"
        '    "thought": "Your reasoning about the current step and why you chose this tool and verification method.",\n'
        '    "tool_name": "The name of the main tool to call.",\n'
        '    "tool_args": { "arg1": "value1" },\n'
        '    "verification_tool_name": "tool_to_check_if_it_worked",\n'
        '    "verification_tool_args": { "arg_for_check": "value_for_check" }\n'
        "}"
    )
    user_prompt = f"""## Main Goal
`{state.task_prompt}`

## Previous Steps
{history_str}

## Your JSON Response:
"""
    return system_prompt, user_prompt


async def reflect_and_plan(
        state: TaskState, llm_query_func: Callable[[str, str], Awaitable[str]]
) -> Dict[str, Any]:
    # ... (function content is unchanged)
    logger.info("🤔 Step: Reflect and Plan")
    system_prompt, user_prompt = construct_planning_prompt(state)
    logger.debug(f"LLM planning prompt:\n---SYSTEM---\n{system_prompt}\n---USER---\n{user_prompt}")
    try:
        llm_response_str = await llm_query_func(system_prompt, user_prompt)
        parsed_json = json.loads(llm_response_str)
        scratchpad = AgentScratchpad.model_validate(parsed_json)
        logger.info(f"✅ Plan generated: Calling tool `{scratchpad.tool_name}`")
        logger.debug(f"🤔 Thought: {scratchpad.thought}")
        return {"latest_plan": scratchpad}
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse or validate LLM plan output. Error: {e}")
        logger.debug(f"LLM raw output was:\n{llm_response_str}")
        raise PlannerError(f"LLM returned malformed plan. Error: {e}") from e
