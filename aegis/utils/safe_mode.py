"""Manages the global safe mode state for tool execution restrictions."""

from typing import Callable

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class UnsafeCommandError(Exception):
    """
    UnsafeCommandError class.
    """

    pass


def safe_mode_required(func: Callable) -> Callable:
    """
    safe_mode_required.
    :param func: Description of func
    :type func: Any
    :return: Description of return value
    :rtype: Any
    """

    def wrapper(*args, **kwargs):
        """
        wrapper.
        :return: Description of return value
        :rtype: Any
        """
        safe_mode = kwargs.get("safe_mode", True)
        if not safe_mode:
            return func(*args, **kwargs)
        raise UnsafeCommandError(
            f"This operation is blocked in safe mode: {func.__name__}"
        )

    logger.error("Error raised during utility operation")
    return wrapper


def warn_if_unsafe(shell_command: str) -> None:
    """
    warn_if_unsafe.
    :param shell_command: Description of shell_command
    :type shell_command: Any
    :return: Description of return value
    :rtype: Any
    """
    banned_tokens = [
        ";",
        "&&",
        "|",
        "`",
        "$(",
        "mkfs",
        "rm -rf",
        "> /dev/sd",
        "dd if=",
        "curl | sh",
    ]
    for token in banned_tokens:
        if token in shell_command:
            raise UnsafeCommandError(
                f"Unsafe token detected in shell command: '{token}'"
            )
    logger.error("Error raised during utility operation")
