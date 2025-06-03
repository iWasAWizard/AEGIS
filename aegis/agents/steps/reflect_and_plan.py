"""Reflects on the prompt and available tools, and plans an appropriate action."""

import json
from typing import Optional
from pydantic import ValidationError

from aegis.utils.logger import setup_logger
from aegis.agents.task_state import TaskState
from aegis.agents.plan_output import PlanOutput
from aegis.utils.llm_query import llm_query
from aegis.registry import list_tools

logger = setup_logger(__name__)


async def reflect_and_plan(state: TaskState) -> Optional[TaskState]:
    """
    Reflects on the task prompt and tool metadata to determine the next step in the plan.

    :param state: Task state including prompt, tool registry, and any prior context.
    :type state: TaskState
    :return: Modified TaskState with planned step embedded, or None if planning fails.
    :rtype: Optional[TaskState]
    """
    logger.info("🔍 Running reflect_and_plan step")

    if state.sensor_outputs:
        logger.debug(
            "Sensor data provided",
            extra={
                "event_type": "sensor_debug",
                "data": {"sensor_keys": list(state.sensor_results.keys())},
            },
        )
    else:
        logger.info("No sensor data provided")

    if not state.task_prompt:
        logger.error("[reflect_and_plan] Missing task prompt")
        raise ValueError("Missing task prompt.")

    available_tools = list_tools()
    if not available_tools:
        logger.warning("[reflect_and_plan] No tools available to planner")
        raise ValueError("No tools available for planning.")

    system_prompt = (
        "You are an AI planner responsible for selecting the next tool to use in a task automation system. "
        "You will be given a high-level task description and a list of available tools. "
        "Your job is to pick one tool and provide its name along with a JSON object of its parameters.\n\n"
        "Respond only with valid JSON in the following format:\n"
        '{\n  "tool_name": "example_tool",\n  "tool_args": { "arg1": "value1", "arg2": 2 }\n}\n\n'
        "Do not include explanations or any output outside this JSON structure."
    )

    user_prompt = (
        f"Task: {state.task_prompt}\n\n"
        f"Available tools: {', '.join(available_tools)}\n\n"
    )

    logger.debug(
        "[reflect_and_plan] Sending prompt to LLM",
        extra={
            "event_type": "planner_prompt",
            "data": {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "model": state.runtime.model,
                "ollama_url": state.runtime.ollama_url,
            },
        },
    )

    llm_output = await llm_query(system_prompt=system_prompt, user_prompt=user_prompt)

    try:
        parsed_json = json.loads(llm_output)
        logger.info(
            "📦 Raw LLM response (parsed):\n" + json.dumps(parsed_json, indent=2)
        )
    except json.JSONDecodeError:
        logger.warning("❗ Failed to decode LLM output as JSON")
        logger.info(f"📦 Raw LLM response (unparsed): {llm_output}")

    # logger.info(
    #     "[reflect_and_plan] LLM raw output",
    #     extra={"event_type": "llm_output", "data": {"output": llm_output}},
    # )

    # try:
    #     plan_raw = json.loads(llm_output)
    #     plan = PlanOutput.model_validate(plan_raw)
    #     state.steps_output["plan"] = plan.model_dump()
    # except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as e:
    #     logger.error(
    #         "[reflect_and_plan] Failed to parse or validate plan output",
    #         extra={
    #             "event_type": "plan_output_error",
    #             "data": {"raw_output": llm_output, "error": str(e)},
    #         },
    #     )
    #     raise ValueError("Failed to extract valid plan output.") from e
    try:
        plan_raw = json.loads(llm_output)
        print(f"✅ Raw decoded plan: {plan_raw}")
        logger.debug(
            "[reflect_and_plan] Decoded JSON plan",
            extra={"event_type": "plan_json", "data": {"decoded": plan_raw}},
        )
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as e:
        import traceback

        logger.error(
            "[reflect_and_plan] Failed to parse or validate plan output",
            extra={
                "event_type": "plan_output_error",
                "data": {
                    "raw_output": llm_output,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            },
        )
        print(
            f"❌ Failed to parse or validate output: {llm_output}\n{traceback.format_exc()}"
        )
        raise ValueError("Failed to extract valid plan output.") from e

    plan = PlanOutput.model_validate(plan_raw)
    state.steps_output["plan"] = plan.model_dump()

    logger.info(
        "✅ Plan accepted",
        extra={
            "event_type": "plan_decision",
            "data": {"tool": plan.tool_name, "arguments": plan.tool_args},
        },
    )

    state.tool_name = plan.tool_name
    state.next_step = "execute_tool"
    return state
