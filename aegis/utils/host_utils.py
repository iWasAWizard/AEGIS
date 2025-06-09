# aegis/utils/host_utils.py
"""
Utility functions for handling host and target specifications.
"""
from typing import Tuple

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_user_host_from_string(host_str: str) -> Tuple[str, str]:
    """Parses a 'user@host' string into a (user, host) tuple.

    This is a centralized helper to ensure consistent handling of remote
    target specifications across all tools.

    :param host_str: The input string, e.g., "user@example.com".
    :type host_str: str
    :return: A tuple containing the user and the host.
    :rtype: Tuple[str, str]
    :raises ValueError: If the string is not in the expected 'user@host' format.
    """
    logger.debug(f"Parsing host string: {host_str}")
    if "@" not in host_str:
        logger.warning(f"Invalid host string format received: {host_str}")
        raise ValueError(f"Host string '{host_str}' must be in 'user@host' format.")
    user, host = host_str.split("@", 1)
    return user, host
