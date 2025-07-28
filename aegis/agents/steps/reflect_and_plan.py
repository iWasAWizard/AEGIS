# aegis/agents/steps/reflect_and_plan.py
"""
The core planning step for the agent.

This module contains the `reflect_and_plan` function, which is responsible
for a single "thought" cycle of the agent. It analyzes the task, reviews the
history, and uses the LLM to decide on the next action to take.
"""

import json
from typing import Dict, Any, List

from pydantic import ValidationError

from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError, ConfigurationError
from aegis.registry import TOOL_REGISTRY
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_tool_schemas(safe_mode_active: bool, tool_allowlist: List[str]) -> str:
    """Gets formatted schema descriptions for all available tools, indicating safety."""
    tool_signatures: List[str] = []
    excluded_tags = {"internal"}

    # If an allow-list is provided, filter the tools to be shown.
    tools_to_show = (
        {name: tool for name, tool in TOOL_REGISTRY.items() if name in tool_allowlist}
        if tool_allowlist
        else TOOL_REGISTRY
    )

    for tool_name, tool_entry in sorted(tools_to_show.items()):
        if any(tag in tool_entry.tags for tag in excluded_tags):
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
    # The 'finish' tool is always available, regardless of the allow-list.
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
        "You are an autonomous agent that achieves goals by selecting one tool at a time. "
        "Your goal is to generate a valid JSON object that represents your next single action."
        "You MUST NOT provide any other text, explanation, or markdown."
    )
    user_prompt = f"""You are an autonomous agent. Your task is to achieve the user's goal by thinking step-by-step and selecting one tool at a time.

## Instructions
1.  **Analyze Goal & History:** Review the user's goal and any previous steps.
2.  **Plan ONE Step:** Decide on the single next action to take.
3.  **Explain Your Thought:** You MUST include a `thought` key. The value must be a brief explanation of your choice.
4.  **Choose ONE Tool:** Select one tool from the 'Available Tools' list.
5.  **Adhere to Schema:** The `tool_args` must be a valid JSON object matching the tool's arguments.

## Available Tools
{get_tool_schemas(safe_mode_active=bool(state.runtime.safe_mode), tool_allowlist=state.runtime.tool_allowlist)}

## Main Goal
`{state.task_prompt}`

## Previous Steps
{history_str}

Now, provide the JSON for your next action.
"""
    return system_prompt, user_prompt


async def reflect_and_plan(state: TaskState) -> Dict[str, Any]:
    """Uses the configured backend provider to generate a validated plan."""
    logger.info("🤔 Step: Reflect and Plan")
    system_prompt, user_prompt = construct_planning_prompt(state)

    if not state.runtime.backend_profile:
        raise ConfigurationError(
            "Backend profile is not set in the current task state."
        )

    try:
        provider = get_provider_for_profile(state.runtime.backend_profile)
        scratchpad = await provider.get_structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=AgentScratchpad,
        )

        logger.info(f"✅ Plan generated: Calling tool `{scratchpad.tool_name}`")
        logger.debug(f"🤔 Thought: {scratchpad.thought}")
        return {"latest_plan": scratchpad}

    except (ValidationError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse or validate LLM plan output. Error: {e}")
        raise PlannerError(f"LLM returned malformed plan. Error: {e}") from e
    except NotImplementedError as e:
        logger.error(
            f"The configured provider does not support structured planning. Error: {e}"
        )
        raise PlannerError(
            f"The backend '{state.runtime.backend_profile}' does not support the required planning features."
        ) from e
    except Exception as e:
        logger.exception("An unexpected error occurred during planning.")
        raise PlannerError(f"An unexpected error occurred during planning: {e}") from e
