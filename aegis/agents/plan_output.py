"""
Schema for the output of the reflect_and_plan step.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PlanOutput(BaseModel):
    """
    PlanOutput contains the structured result of the reflect_and_plan step.

    :param tool_name: Name of the tool the agent should run next.
    :param machine: The target machine or address the tool should operate on.
    :param reason: Optional explanation of why this tool was selected.
    :param steps: Aggregate procedure up to this point in time.
    """

    tool_name: str = Field(..., description="Name of the selected tool")
    tool_args: Dict[str, Any]
    machine: Optional[str] = Field(None, description="Target machine or address")
    reason: Optional[str] = Field(
        None, description="Optional rationale for this choice"
    )
    steps: Optional[List[str]] = Field(default_factory=list)
