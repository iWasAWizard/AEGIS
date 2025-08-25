# aegis/tools/wrappers/slack.py
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from aegis.registry import tool
from aegis.schemas.tool_result import ToolResult
from aegis.executors.slack_exec import SlackExecutor
from aegis.utils.tracing import span  # observability


# ---------- Input models ----------


class SlackSendMessageInput(BaseModel):
    channel: str = Field(..., description="Slack channel ID or name")
    text: str = Field(..., description="Message text")
    thread_ts: Optional[str] = Field(
        default=None,
        description="Optional thread timestamp to reply in a thread",
    )


# ---------- Tools ----------


@tool(
    "slack.send_message",
    SlackSendMessageInput,
    timeout=15,
    description="Post a message to Slack (optionally as a thread reply).",
    category="slack",
    tags=("slack", "chat", "notifications"),
)
def slack_send_message(*, input_data: SlackSendMessageInput) -> ToolResult:
    """
    Send a message to Slack via SlackExecutor.
    Returns a ToolResult with stdout containing API response text (or dry-run preview).
    """
    with span(
        "wrapper.slack.send",
        channel=input_data.channel,
        has_thread=bool(input_data.thread_ts),
    ):
        ex = SlackExecutor()
        return ex.send_message_result(
            channel=input_data.channel,
            text=input_data.text,
            thread_ts=input_data.thread_ts,
        )
