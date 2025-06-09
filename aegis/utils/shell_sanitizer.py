# aegis/utils/shell_sanitizer.py
"""
Implements input sanitization and safety validation logic for prompts and shell commands.
"""
import shlex

import tiktoken

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# --- Prompt Safety ---

BLOCKED_PROMPT_PHRASES = {
    "ignore previous", "shut down", "delete all", "format disk", "rm -rf",
    ":(){", "fork bomb",
}


def is_prompt_safe(text: str) -> bool:
    """Checks if a given prompt contains blacklisted, potentially harmful phrases.

    :param text: The raw prompt string to check.
    :type text: str
    :return: True if the prompt is considered safe, False otherwise.
    :rtype: bool
    """
    lowered = text.lower()
    for phrase in BLOCKED_PROMPT_PHRASES:
        if phrase in lowered:
            logger.warning(f"Potentially unsafe prompt blocked. Triggered by phrase: '{phrase}'")
            return False
    logger.debug("Prompt passed safety check.")
    return True


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimates the number of tokens in a string using the tiktoken library.

    This is a helper function to provide a rough estimate of prompt size, which
    can be useful for debugging or cost estimation with token-based models.

    :param text: The input string to count tokens for.
    :type text: str
    :param model: The model name to use for tokenizer selection (e.g., 'gpt-4').
    :type model: str
    :return: The estimated number of tokens.
    :rtype: int
    """
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(f"No tiktoken encoding found for model '{model}'. Using 'cl100k_base' as fallback.")
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


# --- Shell Safety ---

FORBIDDEN_SHELL_PATTERNS = [
    (";", "Command chaining"),
    ("&&", "Logical AND command chaining"),
    ("||", "Logical OR command chaining"),
    ("|", "Piping"),
    ("`", "Backtick command substitution"),
    ("$(", "Modern command substitution"),
    (">", "File redirection (overwrite)"),
    ("<", "File redirection (input)"),
]


def validate_shell_command(command: str) -> tuple[bool, str]:
    """Validates a shell command against a list of forbidden patterns.

    This function checks for common shell metacharacters that could be used
    for command injection or other malicious activities. It is a basic but
    effective guardrail for tools that execute shell commands.

    :param command: The shell command string to validate.
    :type command: str
    :return: A tuple containing (is_safe: bool, reason: str).
    :rtype: tuple[bool, str]
    """
    for pattern, reason in FORBIDDEN_SHELL_PATTERNS:
        if pattern in command:
            error_reason = f"Unsafe pattern detected: '{pattern}' ({reason})"
            logger.warning(f"Shell command validation failed. {error_reason}. Command: '{command}'")
            return False, error_reason
    logger.debug(f"Shell command validation passed: '{command}'")
    return True, "Command is safe."


def sanitize_shell_arg(arg: str) -> str:
    """Sanitizes a string for safe use as a single shell argument by quoting it.

    This uses `shlex.quote` to ensure that an argument containing spaces or
    shell metacharacters is treated as a single, literal string by the shell,
    preventing command injection vulnerabilities.

    :param arg: The argument string to sanitize.
    :type arg: str
    :return: The shell-escaped argument string.
    :rtype: str
    """
    return shlex.quote(arg)
