"""Contains safety validation functions for inputs and commands,
focused on securing shell operations and tool invocations."""

import tiktoken

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

BLOCKED_PHRASES = {
    "ignore previous",
    "shut down",
    "delete all",
    "format disk",
    "rm -rf",
    ":(){",
    "fork bomb",
}


def is_prompt_safe(text: str) -> bool:
    """Check whether a given prompt appears safe to send to the LLM.

    Currently a placeholder for implementing safety checks like prompt injection detection.

    :param text: Raw prompt string.
    :return: True if safe, False otherwise."""
    lowered = text.lower()
    return not any(bad in lowered for bad in BLOCKED_PHRASES)


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate the number of tokens in a prompt based on whitespace splitting.

    This is a naive token estimate and may not match the tokenizer used by the LLM.

    :param text: Input string to count.
    :type text: str
    :param model: The model to use for token counter.
    :type model: str
    :return: Integer token estimate."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError as e:
        logger.warning(f"Missing expected key: {e}")
        enc = tiktoken.get_encoding("cl100k_base")

    return len(enc.encode(text))


def validate_shell_command(command: str) -> tuple[bool, str]:
    """
    Validate a shell command string for potentially dangerous operations.

    This function checks for disallowed patterns such as command chaining,
    background execution, file redirection, or wildcard expansion.
    The goal is to prevent arbitrary code execution or system damage.

    :param command: The shell command string to validate.
    :return: Tuple containing (is_safe: bool, reason: str)
    """
    forbidden_patterns = [";", "&&", "||", "`", "$(", "|", ">", "<", "*", "&"]
    for pattern in forbidden_patterns:
        if pattern in command:
            return False, f"Unsafe pattern detected: '{pattern}'"
    return True, "Command is safe."


def sanitize_shell_string(raw_string: str) -> str:
    """
    Sanitize a shell string by escaping special characters and removing dangerous constructs.

    This function does not guarantee perfect security, but it reduces
    the risk of shell injection by escaping commonly abused characters.

    :param raw_string: Input string potentially containing unsafe characters.
    :return: A sanitized version safe for shell usage.
    """
    import shlex
    return shlex.quote(raw_string)
