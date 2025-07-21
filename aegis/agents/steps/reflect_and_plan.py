# aegis/agents/steps/reflect_and_plan.py
"""
The core planning step for the agent.

This module contains the `reflect_and_plan` function, which is responsible
for a single "thought" cycle of the agent. It analyzes the task, reviews the
history, and uses the LLM to decide on the next action to take.
"""

import json
import re
from typing import Dict, Any, List, Callable, Awaitable

from pydantic import ValidationError

from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError
from aegis.registry import TOOL_REGISTRY
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_tool_schemas(safe_mode_active: bool) -> str:
    """Gets formatted schema descriptions for all available tools, indicating safety."""
    tool_signatures: List[str] = []
    excluded_tags = {"internal"}
    for tool_name, tool_entry in sorted(TOOL_REGISTRY.items()):
        if (
            any(tag in tool_entry.tags for tag in excluded_tags)
            and tool_name != "query_knowledge_base"
        ):
            continue

        safety_indicator = ""
        if not tool_entry.safe_mode:
            safety_indicator = " [UNSAFE]"
            if safe_mode_active:
                safety_indicator += " (BLOCKED IN CURRENT MODE)"
        elif tool_entry.safe_mode:
            safety_indicator = " [SAFE]"

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
            full_signature = f"- {tool_name}({args_signature}):{safety_indicator} {tool_entry.description}"
            tool_signatures.append(full_signature)
        except Exception as e:
            logger.warning(f"Could not generate signature for tool '{tool_name}': {e}")

    finish_desc = "Call this tool ONLY when the user's entire request has been fully completed or is impossible to complete. Provide a final summary in the 'reason' argument."
    # Finish tool is always considered safe in its operation by the agent.
    tool_signatures.append(
        f"- finish(reason: string, status: string): [SAFE] {finish_desc}"
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
        for i, entry in enumerate(state.history):
            # Ensure tool_args is a dict for json.dumps; it should be from AgentScratchpad
            tool_args_str = json.dumps(
                entry.plan.tool_args or {}
            )  # Handle if tool_args is None
            history_str += (
                f"### Step {i + 1}:\n"
                f"**Thought:** {entry.plan.thought}\n"
                f"**Action:** Called tool `{entry.plan.tool_name}` "
                f"with args `{tool_args_str}`.\n"
                f"**Observation:** `{str(entry.observation)}`\n\n"
            )

    system_prompt = (
        "YOUR ONLY GOAL IS TO RESPOND WITH A SINGLE, VALID JSON OBJECT. DO NOT PROVIDE ANY OTHER TEXT, EXPLANATION, OR MARKDOWN.\n\n"
        "You are an autonomous agent that achieves goals by selecting one tool at a time.\n\n"
        "## Instructions\n"
        "1.  **Analyze Goal & History:** Review the user's goal and any previous steps.\n"
        "2.  **Plan ONE Step:** Decide on the single next action to take.\n"
        "3.  **Explain Your Thought:** You MUST include a `thought` key in your JSON. The value must be a brief explanation of your choice.\n"
        "4.  **Choose ONE Tool:** Select one tool from the 'Available Tools' list.\n"
        "5.  **Adhere to Schema:** The `tool_args` must be a valid JSON object matching the tool's arguments.\n"
        "6.  **JSON ONLY:** Your entire response must be ONLY the JSON object.\n\n"
        "## Available Tools\n"
        f"{get_tool_schemas(safe_mode_active=bool(state.runtime.safe_mode))}\n\n"
        "## Example Response Format\n"
        "{\n"
        '    "thought": "I need to create a directory, so I will use the `create_directory` tool.",\n'
        '    "tool_name": "create_directory",\n'
        '    "tool_args": {\n'
        '        "path": "name_of_directory"\n'
        "    }\n"
        "}\n\n"
        "## Your Turn"
    )
    user_prompt = f"""## Main Goal
`{state.task_prompt}`

## Previous Steps
{history_str}

## Your JSON Response:
"""
    return system_prompt, user_prompt


async def reflect_and_plan(
    state: TaskState, llm_query_func: Callable[..., Awaitable[str]]
) -> Dict[str, Any]:
    """Uses the LLM to reflect on the current state and decide the next action.

    :param state: The current agent task state.
    :type state: TaskState
    :param llm_query_func: The async function to call for LLM queries.
    :type llm_query_func: Callable
    :return: A dictionary with the new `latest_plan`.
    :rtype: Dict[str, Any]
    :raises PlannerError: If the LLM response for the plan is unparsable.
    """
    logger.info("🤔 Step: Reflect and Plan")
    logger.debug(f"Entering reflect_and_plan with state: {repr(state)}")
    system_prompt, user_prompt = construct_planning_prompt(state)

    try:
        llm_response_str = await llm_query_func(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            runtime_config=state.runtime,
        )
        # Attempt to find a JSON block in the response, in case the model ignores instructions
        json_match = re.search(r"\{.*\}", llm_response_str, re.DOTALL)
        if not json_match:
            raise json.JSONDecodeError(
                "No JSON object found in the LLM response.", llm_response_str, 0
            )

        json_str = json_match.group(0)
        parsed_json = json.loads(json_str)
        scratchpad = AgentScratchpad.model_validate(parsed_json)
        logger.info(f"✅ Plan generated: Calling tool `{scratchpad.tool_name}`")
        logger.debug(f"🤔 Thought: {scratchpad.thought}")
        return {"latest_plan": scratchpad}
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse or validate LLM plan output. Error: {e}")
        logger.debug(f"LLM raw output was:\n{llm_response_str}")
        raise PlannerError(f"LLM returned malformed plan. Error: {e}") from e
