# aegis/tools/wrappers/interaction.py
"""
Wrapper tools for direct interaction with the human operator.
"""
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class AskHumanForInputInput(BaseModel):
    """Input for asking a human for input or confirmation.

    :ivar question: The question to ask the human operator.
    :vartype question: str
    """

    question: str = Field(..., description="The question to ask the human operator.")


@register_tool(
    name="ask_human_for_input",
    input_model=AskHumanForInputInput,
    description="Pauses the agent and asks a question to the human operator. The human's response will be the observation for the next step.",
    category="interaction",
    tags=["human-in-the-loop", "interaction", "wrapper"],
    safe_mode=True,
    purpose="Ask a human for guidance, confirmation, or information.",
)
def ask_human_for_input(input_data: AskHumanForInputInput) -> str:
    """
    This tool is a signal to the agent graph to interrupt execution.

    The actual pausing logic is handled by the graph's interruption mechanism.
    This function's return value will be recorded as the observation, confirming
    to the agent that the question has been posed. The human's eventual answer
    will be injected into the state when the task is resumed.

    :param input_data: An object containing the question for the human.
    :type input_data: AskHumanForInputInput
    :return: A confirmation message.
    :rtype: str
    """
    logger.info(f"Posing question to human: '{input_data.question}'")
    return f"The agent has paused and is waiting for a human response to the question: '{input_data.question}'"
