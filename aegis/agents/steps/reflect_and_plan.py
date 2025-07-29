# aegis/agents/steps/reflect_and_plan.py
"""
The core planning step for the agent.

This module contains the `reflect_and_plan` function, which is responsible
for a single "thought" cycle of the agent. It analyzes the task, reviews the
history, and uses the LLM to decide on the next action to take.
"""

import json
from pyexpat.errors import messages
from typing import Dict, Any, List

from pydantic import ValidationError, BaseModel, Field

from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError, ConfigurationError
from aegis.registry import TOOL_REGISTRY
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class RelevantTools(BaseModel):
    """Schema for the LLM's tool selection decision."""

    tool_names: List[str] = Field(
        ..., description="A list of the most relevant tool names for the current task."
    )


def get_all_tool_signatures() -> str:
    """Gets a simple list of all available tool signatures."""
    signatures = []
    for name, tool in TOOL_REGISTRY.items():
        signatures.append(f"- {name}: {tool.description}")
    return "\n".join(signatures)


async def _select_relevant_tools(state: TaskState) -> List[str]:
    """Uses a preliminary LLM call to select a small subset of relevant tools."""
    if not state.runtime.backend_profile:
        raise ConfigurationError("Backend profile is not set.")

    provider = get_provider_for_profile(state.runtime.backend_profile)
    all_signatures = get_all_tool_signatures()

    system_prompt = "You are a helpful assistant. Your task is to select the most relevant tools for the user's request from a provided list. Return your answer as a JSON object."
    user_prompt = f"""
    Based on the user's goal and the conversation history, which of the following tools are the most relevant?
    Please select the top 5-7 most useful tools.

    ## User's Goal
    {state.task_prompt}

    ## Conversation History
    {"No history yet." if not state.history else json.dumps([h.model_dump() for h in state.history], default=str)}

    ## Available Tools
    {all_signatures}
    """
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        selected_tools_model = await provider.get_structured_completion(
            messages, RelevantTools
        )
        logger.info(f"Pre-selected relevant tools: {selected_tools_model.tool_names}")
        return selected_tools_model.tool_names
    except Exception as e:
        logger.warning(
            f"Tool pre-selection failed: {e}. Falling back to using all tools."
        )
        return list(TOOL_REGISTRY.keys())


def get_tool_schemas(tool_allowlist: List[str]) -> str:
    """Gets formatted schema descriptions for a specific list of tools."""
    tool_signatures: List[str] = []

    for tool_name in sorted(tool_allowlist):
        if tool_name not in TOOL_REGISTRY:
            continue
        tool_entry = TOOL_REGISTRY[tool_name]

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

    finish_desc = "Call this tool ONLY when the user's entire request has been fully completed or is impossible to complete."
    tool_signatures.append(f"- finish(reason: string, status: string): {finish_desc}")
    return "\n".join(tool_signatures)


def construct_planning_messages(
    state: TaskState, relevant_tools: List[str]
) -> List[Dict[str, Any]]:
    """Constructs the full message history for the LLM planner."""
    system_prompt = f"""You are an autonomous agent. Your task is to achieve the user's goal by thinking step-by-step and selecting one tool at a time.

    ## Instructions
    1.  **Analyze Goal & History:** Review the user's goal and the history of actions taken so far.
    2.  **Plan ONE Step:** Decide on the single next action. Your response must be a single tool call in JSON format.
    3.  **Use Available Tools:** Select one tool from the provided list. Do not invent tools.
    4.  **Adhere to Schema:** The `tool_args` must be a valid JSON object matching the tool's arguments precisely. The `thought` field is MANDATORY.

    ## Response Format Example
    ```json
    {{
    "thought": "I need to write the user's requested script to a file. The `write_to_file` tool is the most appropriate for this. I will specify the filename and the Python code to be written.",
    "tool_name": "write_to_file",
    "tool_args": {{
        "path": "calculate.py",
        "content": "print(25 * 8)"
    }}
    }}

    Available Tools for this step

    {get_tool_schemas(relevant_tools)}
    """

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.append(
        {"role": "user", "content": f"Here is my request: {state.task_prompt}"}
    )

    for entry in state.history:
        messages.append(
            {"role": "assistant", "content": json.dumps(entry.plan.model_dump())}
        )
        messages.append({"role": "tool", "content": entry.observation})

    return messages


async def reflect_and_plan(state: TaskState) -> Dict[str, Any]:
    """Uses the configured backend provider to generate a validated plan."""
    logger.info("🤔 Step: Reflect and Plan")

    if not state.runtime.backend_profile:
        raise ConfigurationError("Backend profile is not set.")

    try:
        # 1. Select a small subset of relevant tools to reduce prompt size
        relevant_tool_names = await _select_relevant_tools(state)

        # 2. Construct the full conversational history
        messages = construct_planning_messages(state, relevant_tool_names)

        logger.debug(f"--- Full Planning Prompt ---")
        logger.debug(json.dumps(messages, indent=2))
        logger.debug(f"--- End Planning Prompt ---")

        # 3. Call the provider with the structured messages to get the next plan
        provider = get_provider_for_profile(state.runtime.backend_profile)
        logger.debug(f"Using provider '{provider.__class__.__name__}' for planning.")
        scratchpad = await provider.get_structured_completion(
            messages=messages,
            response_model=AgentScratchpad,
        )

        logger.info(f"✅ Plan generated: Calling tool `{scratchpad.tool_name}`")
        logger.debug(f"🤔 Thought: {scratchpad.thought}")
        return {"latest_plan": scratchpad}

    except (ValidationError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse or validate LLM plan output. Error: {e}")
        raise PlannerError(f"LLM returned malformed plan. Error: {e}") from e
    except Exception as e:
        logger.exception("An unexpected error occurred during planning.")
        raise PlannerError(f"An unexpected error occurred during planning: {e}") from e
