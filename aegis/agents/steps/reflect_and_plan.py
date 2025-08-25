# aegis/agents/steps/reflect_and_plan.py
"""
The core planning step for the agent.

This module contains the `reflect_and_plan` function, which is responsible
for a single "thought" cycle of the agent. It analyzes the task, reviews the
history, and uses the LLM to decide on the next action to take.
"""

import json
from typing import Dict, Any, List

from pydantic import ValidationError, BaseModel, Field

from aegis.agents.prompt_builder import PromptBuilder
from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError, ConfigurationError
from aegis.registry import TOOL_REGISTRY
from aegis.schemas.plan_output import AgentScratchpad
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.logger import setup_logger
from aegis.utils.replay_logger import log_replay_event
from aegis.utils.tracing import span

logger = setup_logger(__name__)


class RelevantTools(BaseModel):
    """Schema for the LLM's tool selection decision."""

    tool_names: List[str] = Field(
        ..., description="A list of the most relevant tool names for the current task."
    )


async def _select_relevant_tools(
    state: TaskState, tool_names_to_consider: List[str]
) -> List[str]:
    """Uses a preliminary LLM call to select a small subset of relevant tools."""
    if not state.runtime.backend_profile:
        raise ConfigurationError("Backend profile is not set.")

    provider = get_provider_for_profile(state.runtime.backend_profile)

    # Build temporary summaries for the catalog
    temp_builder = PromptBuilder(state, tool_names_to_consider, provider)
    tool_summaries = await temp_builder.get_tool_summaries()

    system_prompt = (
        "You are a careful planner. Given the task and tool catalog, "
        "select only the tools that are plausibly relevant. Return JSON only."
    )

    user_prompt = f"""
        You are given a task, a short recent history, and a catalog of tools (name + description).
        Pick the smallest set of tools that could help take the next step.

        ## Task
        {state.task}

        ## Last Observation (if any)
        {state.latest_observation or ''}

        ## History (summarized)
        {state.get_history_summary(max_items=4)}

        ## Available Tools
        {json.dumps(tool_summaries, indent=2)}

        ## Required JSON Output Format
        You MUST respond with a single JSON object containing a key "tool_names" with a list
        of strings. Do not add any other text, explanation, or markdown.

        ### Example
        ```json
        {{
        "tool_names": ["tool_name_1", "tool_name_2", "tool_name_3"]
        }}
    """

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        with span(
            "planner.preselect",
            run_id=state.task_id,
            ready_tools=len(tool_names_to_consider),
        ):
            selected_tools_model = await provider.get_structured_completion(
                messages, RelevantTools, state.runtime
            )
        # Only keep tools that were in the original catalog
        valid_selected_tools = [
            name
            for name in selected_tools_model.tool_names
            if name in tool_names_to_consider
        ]
        logger.info(f"Pre-selected relevant tools: {valid_selected_tools}")
        return valid_selected_tools or tool_names_to_consider
    except (ValidationError, json.JSONDecodeError) as e:
        logger.warning(
            f"Tool pre-selection failed validation/JSON parse; falling back to full list. Error: {e}"
        )
        return tool_names_to_consider


async def reflect_and_plan(state: TaskState) -> Dict[str, Any]:
    """Uses the configured backend provider to generate a validated plan."""
    logger.info("🤔 Step: Reflect and Plan")

    if not state.runtime.backend_profile:
        raise ConfigurationError("Backend profile is not set.")

    try:
        provider = get_provider_for_profile(state.runtime.backend_profile)

        if state.runtime.tool_allowlist:
            available_tool_names = state.runtime.tool_allowlist
        else:
            available_tool_names = list(TOOL_REGISTRY.keys())

        threshold = state.runtime.tool_selection_threshold or 20
        if len(available_tool_names) > threshold:
            relevant_tool_names = await _select_relevant_tools(
                state, available_tool_names
            )
        else:
            relevant_tool_names = available_tool_names

        # Track allowed tools for telemetry
        allowed_tools = list(relevant_tool_names)

        builder = PromptBuilder(state, relevant_tool_names, provider)
        messages = await builder.build()

        logger.debug("--- Full Planning Prompt ---")
        logger.debug(json.dumps(messages, indent=2))
        logger.debug("--- End Planning Prompt ---")

        log_replay_event(state.task_id, "PLANNER_INPUT", {"messages": messages})

        try:
            with span(
                "planner.plan",
                run_id=state.task_id,
                ready_tools=len(allowed_tools),
            ):
                scratchpad = await provider.get_structured_completion(
                    messages=messages,
                    response_model=AgentScratchpad,
                    runtime_config=state.runtime,
                )
        except ValidationError as e:
            logger.warning("LLM plan failed validation. Attempting self-correction...")
            remediation_prompt = (
                f"The last JSON response you produced did not validate:\n\n{e}\n\n"
                "Respond again with a corrected JSON object that strictly matches the expected schema. "
                "Your response MUST be only the corrected JSON object and nothing else."
            )
            repair_messages = messages[:-1] + [
                {"role": "user", "content": remediation_prompt}
            ]
            log_replay_event(
                state.task_id, "PLANNER_REPAIR_INPUT", {"messages": repair_messages}
            )

            try:
                with span(
                    "planner.repair",
                    run_id=state.task_id,
                    ready_tools=len(allowed_tools),
                ):
                    scratchpad = await provider.get_structured_completion(
                        messages=repair_messages,
                        response_model=AgentScratchpad,
                        runtime_config=state.runtime,
                    )
                logger.info("✅ Self-correction successful. Plan is now valid.")
            except Exception as final_e:
                logger.error(
                    f"Planner remediation attempt failed; aborting planning step. Error: {final_e}"
                )
                raise

        log_replay_event(
            state.task_id, "PLANNER_OUTPUT", {"plan": scratchpad.model_dump()}
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
