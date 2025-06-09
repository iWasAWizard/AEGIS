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

from aegis.agents.plan_output import AgentScratchpad
from aegis.agents.task_state import TaskState
from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_tool_schemas() -> str:
    """
    Generates a compact, human-readable list of tool signatures instead of
    a verbose JSON schema. This significantly reduces the prompt token count.
    """
    tool_signatures: List[str] = []
    excluded_tags = {"internal"}

    for tool_name, tool_entry in sorted(TOOL_REGISTRY.items()):
        if (
            any(tag in tool_entry.tags for tag in excluded_tags)
            and tool_name != "query_knowledge_base"
        ):
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
            full_signature = (
                f"- {tool_name}({args_signature}): {tool_entry.description}"
            )
            tool_signatures.append(full_signature)

        except Exception as e:
            logger.warning(f"Could not generate signature for tool '{tool_name}': {e}")

    # Manually add the special 'finish' tool
    tool_signatures.append(
        "- finish(reason: string, status: string): Call this tool to signal that the task is complete. Provide a summary of the outcome."
    )

    return "\n".join(tool_signatures)


def construct_planning_prompt(state: TaskState) -> tuple[str, str]:
    """Constructs the full system and user prompts for the LLM planner."""
    history_str = ""
    if not state.history:
        history_str = (
            "This is the first step. Begin by thinking about the user's request."
        )
    else:
        for i, (scratchpad, result) in enumerate(state.history):
            history_str += (
                f"### Step {i + 1}:\n"
                f"**Thought:** {scratchpad.thought}\n"
                f"**Action:** Called tool `{scratchpad.tool_name}` "
                f"with args `{json.dumps(scratchpad.tool_args)}`.\n"
                f"**Observation:** `{str(result)}`\n\n"
            )

    system_prompt = f"""You are AEGIS, an autonomous agent. Your goal is to complete the user's task by thinking step-by-step and using the available tools.

## Instructions
1.  **Analyze the Goal:** Review the user's main goal.
2.  **Review History:** Look at the 'Previous Steps' to understand what you have already done.
3.  **Consult Memory (Optional but Recommended):** If you are unsure how to proceed, have encountered an error, or want to see a past example, use the `query_knowledge_base` tool. This tool helps you learn from past experiences. Ask it a question like "how to check disk space" or "what causes a permission denied error".
4.  **Think:** In the `thought` field, reason about the current situation. Decide if the task is complete, or what the best next step is. If you've learned something from your memory, mention it. If the task is complete, you MUST use the `finish` tool.
5.  **Choose ONE Tool:** Select a single tool from the 'Available Tools' list.
6.  **Provide Arguments:** Fill in the `tool_args` with the correct arguments for the chosen tool.
7.  **Respond ONLY with a valid JSON object** matching the required format. Do not add any text, comments, or explanations before or after the JSON.

## Available Tools
The tools are provided in a compact function-signature format: `tool_name(argument: type, ...): description`
{get_tool_schemas()}

## Response Format
You must respond with a single JSON object with the following keys: "thought", "tool_name", "tool_args".
{{
    "thought": "Your reasoning about the current step and why you chose this tool.",
    "tool_name": "The name of the tool you are calling.",
    "tool_args": {{ "arg1": "value1", "arg2": "value2" }}
}}
"""

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
    """Uses an LLM to reflect on the current state and plan the next action.

    :param state: The current state of the agent's task.
    :type state: TaskState
    :param llm_query_func: The async function to call for LLM queries.
    :type llm_query_func: Callable
    :return: A dictionary containing the newly created `AgentScratchpad` under the key 'latest_plan'.
    :rtype: Dict[str, Any]
    """
    logger.info("🤔 Step: Reflect and Plan")
    system_prompt, user_prompt = construct_planning_prompt(state)

    logger.debug(
        f"LLM planning prompt:\n---SYSTEM---\n{system_prompt}\n---USER---\n{user_prompt}"
    )

    llm_response_str = await llm_query_func(system_prompt, user_prompt)

    try:
        # The LLM output format remains the same, so no changes needed here.
        parsed_json = json.loads(llm_response_str)
        scratchpad = AgentScratchpad.model_validate(parsed_json)
        logger.info(f"✅ Plan generated: Calling tool `{scratchpad.tool_name}`")
        logger.debug(f"🤔 Thought: {scratchpad.thought}")
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse or validate LLM plan output. Error: {e}")
        logger.debug(f"LLM raw output was:\n{llm_response_str}")
        scratchpad = AgentScratchpad(
            thought=f"The last attempt to generate a plan failed. The LLM returned invalid output that could not be parsed. Error: {e}. I will now terminate the task to avoid a loop.",
            tool_name="finish",
            tool_args={
                "reason": "Planning phase failed due to malformed LLM response.",
                "status": "failure",
            },
        )

    return {"latest_plan": scratchpad}
