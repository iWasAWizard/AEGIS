# aegis/executors/slack_exec.py
"""
Provides a client for executing Slack operations via the slack_sdk.
"""
from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.schemas.settings import settings
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False


class SlackExecutor:
    """A client for sending messages to Slack."""

    def __init__(self):
        if not SLACK_SDK_AVAILABLE:
            raise ToolExecutionError("The 'slack_sdk' library is not installed.")

        token = settings.SLACK_BOT_TOKEN
        if not token:
            raise ConfigurationError(
                "SLACK_BOT_TOKEN must be set in the environment or .env file."
            )

        self.client = WebClient(token=token)
        try:
            # Test authentication and token validity
            auth_test = self.client.auth_test()
            if not auth_test.get("ok"):
                raise ConfigurationError(
                    f"Slack token is invalid: {auth_test.get('error')}"
                )
            logger.info(
                f"Successfully connected to Slack as user '{auth_test['user']}'."
            )
        except SlackApiError as e:
            logger.error(f"Failed to connect to Slack: {e.response['error']}")
            raise ConfigurationError(
                f"Failed to connect to Slack: {e.response['error']}"
            )

    def send_message(self, channel: str, message: str) -> str:
        """Sends a message to a specified Slack channel."""
        try:
            response = self.client.chat_postMessage(channel=channel, text=message)
            ts = response.get("ts")
            logger.info(
                f"Successfully sent message to Slack channel '{channel}' (timestamp: {ts})."
            )
            return f"Message sent to channel '{channel}' successfully."
        except SlackApiError as e:
            error_msg = f"Failed to send Slack message to channel '{channel}': {e.response['error']}"
            logger.error(error_msg)
            raise ToolExecutionError(error_msg)
