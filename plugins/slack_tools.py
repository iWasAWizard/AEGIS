# aegis/plugins/slack_tools.py
"""
A tool for sending messages to a Slack workspace.
"""
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.slack_exec import SlackExecutor
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# --- Input Models ---


class SlackSendMessageInput(BaseModel):
    """Input model for sending a message to Slack.

    :ivar channel: The Slack channel to post to (e.g., '#general', '@username').
    :vartype channel: str
    :ivar message: The text message to send.
    :vartype message: str
    """

    channel: str = Field(
        ...,
        description="The Slack channel, private group, or user to post to (e.g., '#alerts', '@username').",
    )
    message: str = Field(..., description="The text of the message to send.")


# --- Tools ---


@register_tool(
    name="slack_send_message",
    input_model=SlackSendMessageInput,
    description="Sends a message to a specified Slack channel, private group, or user.",
    category="communication",
    tags=["slack", "native", "notification"],
    safe_mode=True,  # Sending messages is generally considered a safe, non-destructive action.
)
def slack_send_message(input_data: SlackSendMessageInput) -> str:
    """
    Uses the SlackExecutor to send a message.

    :param input_data: The validated input data for the tool.
    :type input_data: SlackSendMessageInput
    :return: A string confirming that the message was sent.
    :rtype: str
    """
    logger.info(f"Executing tool: slack_send_message to channel '{input_data.channel}'")
    try:
        executor = SlackExecutor()
        return executor.send_message(
            channel=input_data.channel, message=input_data.message
        )
    except Exception as e:
        logger.exception("slack_send_message tool failed during execution.")
        raise ToolExecutionError(f"Failed to send Slack message: {e}")
