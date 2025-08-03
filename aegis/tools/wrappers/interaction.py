# aegis/tools/wrappers/interaction.py
"""
Tools for agent-meta-actions and human-in-the-loop interactions.
"""
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class AskHumanForInputInput(BaseModel):
    """Input for asking a human for input.

    :ivar question: The question to ask the human operator.
    :vartype question: str
    """

    question: str = Field(..., description="The question to ask the human operator.")


class ClearShortTermMemoryInput(BaseModel):
    """Input for clearing the agent's short-term memory. Takes no arguments."""

    pass


@register_tool(
    name="ask_human_for_input",
    input_model=AskHumanForInputInput,
    description="Pauses the task and asks the human operator for input or confirmation. Use this when you are stuck or need permission for a sensitive action.",
    category="interaction",
    tags=["interaction", "human-in-the-loop", "pause"],
    safe_mode=True,
    purpose="Ask the human operator for guidance or permission.",
)
def ask_human_for_input(input_data: AskHumanForInputInput) -> str:
    """
    Signals the agent graph to interrupt execution and wait for human feedback.
    The actual pausing is handled by the graph's interrupt logic.
    """
    logger.info(f"Pausing to ask human for input: '{input_data.question}'")
    return f"The agent has paused and is waiting for human input. The question is: '{input_data.question}'"


@register_tool(
    name="clear_short_term_memory",
    input_model=ClearShortTermMemoryInput,
    description="Clears the agent's short-term conversation history. Use this to reduce context size or to start a new, unrelated sub-task without being influenced by past steps.",
    category="interaction",
    tags=["interaction", "memory", "context"],
    safe_mode=True,
    purpose="Clear the conversational history to start a sub-task fresh.",
)
def clear_short_term_memory(input_data: ClearShortTermMemoryInput) -> str:
    """
    Signals the execute_tool step to clear the agent's history.
    This function itself is a no-op; the logic is in the execution step.
    """
    return "Agent's short-term memory (conversation history) has been cleared."
