from typing import Dict, Any

from pydantic import BaseModel, Field


class LLMPlanResponse(BaseModel):
    """
    Represents the LLMPlanResponse class.

    Holds the structured output returned by the LLM when generating a task plan.
    """

    machine: str = Field(...)
    tool: str = Field(...)
    args: Dict[str, Any] = Field(...)
