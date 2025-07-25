# aegis/tools/wrappers/evaluation.py
"""
Tools for programmatic evaluation of agent performance.
"""
from typing import Dict, Any

from pydantic import BaseModel, Field

from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.providers.base import BackendProvider
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

try:
    import instructor
    from openai import OpenAI
except ImportError:
    instructor = None
    OpenAI = None

logger = setup_logger(__name__)


class Judgement(BaseModel):
    """Schema for a structured LLM judgement."""

    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="The integer score from 1 to 5, where 1 is a complete failure and 5 is a perfect match.",
    )
    rationale: str = Field(
        ..., description="A detailed rationale explaining the score."
    )


class LLMJudgeInput(BaseModel):
    """Input for the llm_judge tool."""

    task_prompt: str = Field(..., description="The original task prompt for the agent.")
    expected_output: str = Field(
        ..., description="The ideal or 'golden' output for the task."
    )
    actual_output: str = Field(
        ..., description="The actual output produced by the agent."
    )


@register_tool(
    name="llm_judge",
    input_model=LLMJudgeInput,
    description="Uses a high-quality LLM to evaluate an agent's output against an expected result.",
    category="evaluation",
    tags=["evaluation", "internal", "llm"],
    safe_mode=True,
    purpose="Programmatically score an agent's performance on a given task.",
)
async def llm_judge(
    input_data: LLMJudgeInput, state: TaskState, provider: BackendProvider
) -> Dict[str, Any]:
    """
    Asks a provider to act as a judge, scoring an agent's output.
    """
    if not instructor or not OpenAI:
        raise ToolExecutionError(
            "The 'instructor' and 'openai' libraries are required for this tool."
        )

    logger.info("⚖️  Executing tool: llm_judge")

    system_prompt = (
        "You are a meticulous and impartial evaluator for an autonomous agent framework. "
        "Your task is to score an AI agent's performance on a scale of 1 to 5. "
        "You must compare the agent's actual output to the expected 'golden' output, in the context of the original task. "
        "Provide a detailed rationale for your score. Your response MUST be a valid JSON object conforming to the specified schema."
    )
    user_prompt = f"""
    ## Original Task Prompt
    `{input_data.task_prompt}`

    ## Expected Output (Golden Answer)
    {input_data.expected_output}

    ## Agent's Actual Output
    {input_data.actual_output}

    Based on the above, please provide your score and rationale.
    A score of 1 means the agent completely failed or produced a dangerously incorrect result.
    A score of 3 means the agent understood the goal but failed to execute it perfectly.
    A score of 5 means the agent's output perfectly matches the intent of the expected output.
    """

    try:
        # This tool is provider-aware, so it uses the provider passed into it
        # which is determined by the runtime state's backend_profile.
        judgement = await provider.get_structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=Judgement,
        )
        return judgement.model_dump()
    except Exception as e:
        logger.exception("llm_judge tool failed during execution.")
        raise ToolExecutionError(f"LLM judgement failed: {e}")
