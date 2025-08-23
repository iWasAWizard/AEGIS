# aegis/executors/slack_exec.py
"""
Provides a client for sending messages to Slack via slack_sdk.
"""
from typing import Optional

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time

logger = setup_logger(__name__)

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False


class SlackExecutor:
    """A minimal Slack client for posting messages."""

    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize the Slack executor.

        :param bot_token: Slack bot token; if None, attempt to read from settings/env.
        :type bot_token: Optional[str]
        """
        if not SLACK_SDK_AVAILABLE:
            raise ToolExecutionError("The 'slack_sdk' library is not installed.")

        if not bot_token:
            from aegis.schemas.settings import settings

            bot_token = settings.SLACK_BOT_TOKEN

        if not bot_token:
            raise ConfigurationError("SLACK_BOT_TOKEN must be configured.")

        self.client = WebClient(token=bot_token)

    def send_message(
        self, channel: str, text: str, thread_ts: Optional[str] = None
    ) -> str:
        """
        Send a message to a Slack channel or thread.

        :param channel: Channel ID (e.g., C12345) or channel name with '#'.
        :type channel: str
        :param text: Message text.
        :type text: str
        :param thread_ts: Optional thread timestamp to reply in thread.
        :type thread_ts: Optional[str]
        :return: Message timestamp of the posted message.
        :rtype: str
        """
        try:
            resp = self.client.chat_postMessage(
                channel=channel, text=text, thread_ts=thread_ts
            )
            return resp["ts"]
        except SlackApiError as e:
            raise ToolExecutionError(f"Slack API error: {e}") from e
        except Exception as e:
            raise ToolExecutionError(f"Slack error: {e}") from e


# === ToolResult wrappers ===
def _now_ms() -> int:
    return int(time.time() * 1000)


def _error_type_from_exception(e: Exception) -> str:
    msg = str(e).lower()
    if "timeout" in msg:
        return "Timeout"
    if "permission" in msg or "auth" in msg:
        return "Auth"
    if "not found" in msg or "no such" in msg:
        return "NotFound"
    if "parse" in msg or "json" in msg:
        return "Parse"
    return "Runtime"


class SlackExecutorToolResultMixin:
    def send_message_result(
        self, channel: str, text: str, thread_ts: str | None = None
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="slack.send_message", args=redact_for_log({"channel": channel})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] slack.send_message",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.send_message(channel=channel, text=text, thread_ts=thread_ts)
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"channel": channel},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"channel": channel},
            )


SlackExecutor.send_message_result = SlackExecutorToolResultMixin.send_message_result
