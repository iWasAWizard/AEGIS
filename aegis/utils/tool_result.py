"""Parses and summarizes tool outputs for structured consumption or reporting."""

from typing import Optional, Any

from pydantic import BaseModel

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class ToolResult(BaseModel):
    """
    Represents the ToolResult class.

    Use this to standardize the structure of a tool's return value, including its result, metadata, and execution time.
    """

    logger.debug("Formatting tool result for return")
    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    returncode: int = 0
    error: Optional[str] = None
    data: Optional[Any] = None

    def to_dict(self) -> dict:
        """
        to_dict.
        :return: Description of return value
        :rtype: Any
        """
        return self.dict(exclude_none=True)
