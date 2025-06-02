"""Implements input sanitization logic for shell and subprocess calls to prevent command injection or misuse."""

import shlex

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def is_shell_safe(cmd: str) -> dict:
    """
    is_shell_safe.
    :param cmd: Description of cmd
    :type cmd: Any
    :return: Description of return value
    :rtype: Any
    """
    blacklist = [
        ("rm -rf", "Destructive delete"),
        ("shutdown", "System shutdown"),
        ("reboot", "System reboot"),
        (";", "Chained command"),
        ("&&", "Logical AND"),
        ("||", "Logical OR"),
        ("|", "Pipe"),
        ("$(", "Command substitution"),
        ("`", "Backtick execution"),
        ("mkfs", "Filesystem format"),
        ("dd if", "Disk overwrite"),
        ("kill -9 1", "Kill init process"),
    ]
    cmd_lower = cmd.lower()
    for token, reason in blacklist:
        if token in cmd_lower:
            logger.warning(f"Unsafe token detected in command: {token} ({reason})")
            return {"valid": False, "reason": f"Unsafe token '{token}': {reason}"}
    return {"valid": True}


def sanitize_shell_arg(arg: str) -> str:
    """
    sanitize_shell_arg.
    :param arg: Description of arg
    :type arg: Any
    :return: Description of return value
    :rtype: Any
    """
    return shlex.quote(arg)


def sanitize_command(raw_cmd: str) -> str:
    """
    sanitize_command.
    :param raw_cmd: Description of raw_cmd
    :type raw_cmd: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.debug(f"Sanitizing command: {raw_cmd}")
    tokens = shlex.split(raw_cmd)
    safe_tokens = [sanitize_shell_arg(token) for token in tokens]
    cleaned = " ".join(safe_tokens)
    logger.debug(f"Sanitized command: {cleaned}")
    return cleaned
