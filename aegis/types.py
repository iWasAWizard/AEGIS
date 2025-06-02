from pydantic import BaseModel
from typing import Dict, Any


class ToolCall(BaseModel):
    """
    Represents a request to invoke a specific tool with input arguments.
    """

    tool: str
    input: Dict[str, Any]
