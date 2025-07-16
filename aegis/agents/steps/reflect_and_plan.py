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

    finish_desc = "Call this to signal that the task is complete. Provide a summary of the outcome."
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
        "You are AEGIS, an autonomous agent. Your goal is to complete the user's task by thinking "
        "step-by-step and using the available tools.\n\n"
        "## Instructions\n"
        "1.  **Analyze Goal & History:** Carefully review the user's overall goal and all previous steps (thoughts, actions, observations).\n"
        "2.  **Strict Tool Adherence:** You **MUST ONLY** choose a tool name from the 'Available Tools' list provided below. Do not invent tool names. If you previously tried a tool that was 'not found in registry', pick a different, valid tool from the list.\n"
        "3.  **Thought Process:** In the `thought` field, explain your reasoning for the current step, why you are choosing a specific tool, and how it helps achieve the user's goal. If a previous step failed, explain how you are adjusting your plan.\n"
        "4.  **Local vs. Remote Operations:** Pay attention to whether the task requires actions on the 'local' machine (where AEGIS is running) or a 'remote' machine. \n"
        "    - For **local** file operations (create, write, read, delete files on the machine AEGIS runs on), use tools like `run_local_command` (if not in safe mode and command is simple), or look for specific safe local file tools if available in the list.\n"
        "    - For **remote** operations, tools will often require a `machine_name` argument. Ensure this machine is defined and accessible. If a remote tool fails due to 'Machine not found', the task likely implies local operations.\n"
        "5.  **Safe Mode Awareness:** If a tool fails with 'blocked by safe mode', you **MUST NOT** try that tool or other [UNSAFE] tools again. Find a [SAFE] alternative or use `finish` with `status: 'failure'` explaining the restriction.\n"
        "6.  **Answering User Questions:** If the goal is to answer a question and you have determined the answer (from a tool or internal knowledge), you **MUST** use the `finish` tool. The answer **MUST** be in the `reason` argument, `status: 'success'`.\n"
        "7.  **Plan Verification (Optional):** For actions (not `finish`), consider a `verification_tool_name` and `verification_tool_args` to check the action's success.\n"
        "8.  **Backend Agnostic Tools**: Tools like `ingest_document` and `retrieve_knowledge` interact with the configured backend. Use them for RAG operations when the task requires it.\n"
        "9.  **Finishing the Task:** When the user's goal is fully achieved or if you determine it cannot be completed (due to errors, safe mode, or lack of suitable tools), you **MUST** use the `finish` tool. Provide a clear `reason` and set `status` ('success', 'failure', 'partial').\n"
        "10. **JSON Output ONLY:** Respond ONLY with a single, valid JSON object as described in 'Response Format'. No other text.\n\n"
        "## Available Tools\n"
        f"{get_tool_schemas(safe_mode_active=bool(state.runtime.safe_mode))}\n\n"
        "## Response Format\n"
        "You must respond with a single JSON object. The `verification` fields are optional (and not used with `finish`).\n"
        "Example for a general tool:\n"
        "{\n"
        '    "thought": "Your reasoning about the current step and why you chose this tool and verification method.",\n'
        '    "tool_name": "The name of the main tool to call.",\n'
        '    "tool_args": { "arg1": "value1" },\n'
        '    "verification_tool_name": "tool_to_check_if_it_worked",\n'
        '    "verification_tool_args": { "arg_for_check": "value_for_check" }\n'
        "}\n"
        "Example for using the `finish` tool when providing an answer:\n"
        "{\n"
        '    "thought": "I have determined the answer to the user_s question. The answer is XYZ.",\n'
        '    "tool_name": "finish",\n'
        '    "tool_args": { "reason": "The answer is XYZ.", "status": "success" },\n'
        '    "verification_tool_name": null,\n'
        '    "verification_tool_args": null\n'
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
        parsed_json = json.loads(llm_response_str)
        scratchpad = AgentScratchpad.model_validate(parsed_json)
        logger.info(f"✅ Plan generated: Calling tool `{scratchpad.tool_name}`")
        logger.debug(f"🤔 Thought: {scratchpad.thought}")
        return {"latest_plan": scratchpad}
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse or validate LLM plan output. Error: {e}")
        logger.debug(f"LLM raw output was:\n{llm_response_str}")
        raise PlannerError(f"LLM returned malformed plan. Error: {e}") from e
