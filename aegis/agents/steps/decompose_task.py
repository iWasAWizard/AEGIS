# aegis/agents/steps/decompose_task.py
"""
Agent step for decomposing a high-level goal into a sequence of sub-goals.
"""
from typing import Dict, Any, List

from pydantic import BaseModel, Field

from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError, ConfigurationError
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class SubGoalList(BaseModel):
    """Schema for the LLM's sub-goal decomposition."""

    sub_goals: List[str] = Field(
        ...,
        description="A list of concise, actionable sub-goals that break down the user's main request.",
    )


async def decompose_task(state: TaskState) -> Dict[str, Any]:
    """
    Performs a preliminary LLM call to break down the main goal into sub-goals.
    """
    logger.info("分解 Step: Decompose Task into Sub-Goals")

    if not state.runtime.backend_profile:
        raise ConfigurationError("Backend profile is not set.")

    provider = get_provider_for_profile(state.runtime.backend_profile)

    system_prompt = "You are a strategic planner. Your task is to decompose a user's complex request into a concise, numbered list of actionable sub-goals. The sub-goals should represent a logical, high-level plan to achieve the overall objective. Respond with a JSON object containing a list of these sub-goals."
    user_prompt = f"""
    Please decompose the following user request into a list of high-level sub-goals.

    ## User Request
    {state.task_prompt}

    ## Required JSON Output Format
    You MUST respond with a single JSON object containing a single key, "sub_goals", which is a list of strings. Do not add any other text, explanation, or markdown.

    ### Example
    ```json
    {{
      "sub_goals": [
        "First, discover all active services on the target machine.",
        "Second, analyze the configuration of the web server.",
        "Finally, generate a report summarizing the findings."
      ]
    }}
    ```
    """

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        sub_goal_model = await provider.get_structured_completion(
            messages, SubGoalList, state.runtime
        )

        sub_goals = sub_goal_model.sub_goals
        logger.info(f"Decomposed task into {len(sub_goals)} sub-goals.")
        for i, goal in enumerate(sub_goals):
            logger.info(f"  - Sub-goal {i+1}: {goal}")

        return {"sub_goals": sub_goals, "current_sub_goal_index": 0}

    except Exception as e:
        logger.error(
            f"Failed to decompose task. Error: {e}. Proceeding with flat planning."
        )
        # Fallback: if decomposition fails, just return an empty list and proceed.
        return {"sub_goals": [], "current_sub_goal_index": 0}
