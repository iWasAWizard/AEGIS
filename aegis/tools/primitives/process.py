"""
Primitive tools for interacting with system processes.

Includes operations for listing processes, checking for active tasks,
and identifying resource usage on the local machine.
"""

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

logger.debug("Loaded process primitives module")
