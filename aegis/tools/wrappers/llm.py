# aegis/tools/wrappers/llm.py
"""
Wrapper tools for allowing the agent to directly interact with its own backend LLM.
"""
from pydantic import BaseModel, Field

from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class InvokeLlmInput(BaseModel):
    """Input for invoking the backend LLM with a specific prompt.

    :ivar system_prompt: The system-level instruction for the LLM.
    :vartype system_prompt: str
    :ivar user_prompt: The user-level question or instruction for the LLM.
    :vartype user_prompt: str
    """

    system_prompt: str = Field(
        ..., description="The system-level instruction for the LLM."
    )
    user_prompt: str = Field(
        ..., description="The user-level question or instruction for the LLM."
    )


@register_tool(
    name="invoke_llm",
    input_model=InvokeLlmInput,
    description="Asks a question to a general-purpose AI. Use this for tasks requiring creativity, summarization, or rephrasing. Do NOT use this for tasks that a more specific tool can accomplish.",
    category="llm",
    tags=["llm", "reasoning", "backend", "provider-aware"],
    safe_mode=True,
    purpose="Leverage the backend LLM for general-purpose reasoning or text generation.",
)
async def invoke_llm(
    input_data: InvokeLlmInput, state: TaskState, provider: BackendProvider
) -> str:
    """
    Uses the active backend provider to perform a generic LLM completion.

    This tool gives the agent a "meta" capability to use its own brain for
    tasks that don't fit a more specific tool, like summarizing a large block
    of text it has gathered.

    :param input_data: The system and user prompts for the LLM.
    :type input_data: InvokeLlmInput
    :param state: The current agent task state (used to get runtime config).
    :type state: TaskState
    :param provider: The active backend provider instance.
    :type provider: BackendProvider
    :return: The string response from the LLM.
    :rtype: str
    """
    logger.info(f"Invoking backend LLM with prompt: '{input_data.user_prompt[:50]}...'")
    try:
        # Refined prompt to give the sub-LLM call more context.
        system_prompt = (
            "You are a sub-module of a larger autonomous agent. "
            "Your purpose is to assist the main agent with a specific reasoning or text-generation task. "
            "Provide a direct, concise answer to the user prompt based on the system instructions you are given."
            f"\n\n--- Main Agent's System Instruction ---\n{input_data.system_prompt}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_data.user_prompt},
        ]
        # Use the existing runtime config from the current state for the call
        response = await provider.get_completion(messages, state.runtime)
        return response
    except Exception as e:
        logger.exception("invoke_llm tool failed.")
        raise ToolExecutionError(f"Direct LLM invocation failed: {e}")