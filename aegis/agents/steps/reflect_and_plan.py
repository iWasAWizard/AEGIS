import json

from aegis.agents.llm_output_schema import LLMPlanResponse
from aegis.agents.task_state import TaskState, attach_runtime
from aegis.utils.llm_query import llm_query
from aegis.utils.logger import setup_logger
from aegis.utils.sensor_formatter import format_sensor_context

logger = setup_logger(__name__)


async def reflect_and_plan(state: TaskState) -> TaskState:
    """
    reflect_and_plan.
    :param state: Description of state
    :type state: Any
    :return: Description of return value
    :rtype: Any
    """
    # pylint: disable=protected-access
    if not hasattr(state, "_llm_query_fn") or state._llm_query_fn is None:
        state = attach_runtime(state, llm_query_fn=llm_query)

    logger.info("🔍 Running reflect_and_plan step")
    planning_prompt = f'You are an expert AI planner. Your job is to choose the best tool and arguments' \
                      f'to accomplish the following task:' \
                      f'' \
                      f'TASK:' \
                      f'{state.task_prompt}' \
                      f'' \
                      f'CONTEXT:' \
                      f'{format_sensor_context(state.sensor_outputs)}' \
                      f'' \
                      f'INSTRUCTIONS:' \
                      f'You must return a single JSON object with this structure:' \
                      f'' \
                      f'{{' \
                      f'  "machine": "<machine ID or hostname>",' \
                      f'  "tool": "<tool name, exactly as registered>",' \
                      f'  "args": {{' \
                      f'    "<argument>": "<value>"' \
                      f'  }}' \
                      f'}}' \
                      f'' \
                      f'Respond ONLY with the JSON object. Do not include any commentary or formatting.'
    llm_response = await state.llm_query("Reflect and plan your next steps.", planning_prompt)
    validated = None
    try:
        parsed = json.loads(llm_response)
        logger.debug(f"[reflect_and_plan] Raw LLM output:\n{llm_response}")
        validated = LLMPlanResponse(**parsed)
        state.tool_request = validated
        logger.info(
            f"✅ Plan accepted: tool={validated.tool}, machine={validated.machine}"
        )
    except Exception as e:
        logger.error(f"[reflect_and_plan] Failed to parse or validate plan: {e}")
        state.tool_request = None
    if validated is not None:
        logger.debug(f"Validated plan payload: {validated.model_dump_json(indent=2)}")
    else:
        logger.warning("[reflect_and_plan] No valid plan returned from planning agent.")
    return state
