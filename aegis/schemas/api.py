# aegis/schemas/api.py
"""
Pydantic schemas for defining the data contracts of the FastAPI API.

These models are used for request validation and, more importantly, for
response serialization to ensure that the API always returns a consistent,
well-defined structure.
"""
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field


class HistoryStepResponse(BaseModel):
    """Represents a single step of the agent's execution history in an API response."""

    thought: str
    tool_name: str
    tool_args: Dict[str, Any]
    tool_output: str


class LaunchResponse(BaseModel):
    """Defines the structure of the response from the /launch and /resume endpoints."""

    task_id: str
    summary: Optional[str] = None
    history: List[HistoryStepResponse]
    status: Optional[str] = Field(
        default="COMPLETED",
        description="The final status of the task ('COMPLETED', 'PAUSED', etc.).",
    )
