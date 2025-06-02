"""
Schema for launching a task with custom config and runtime options.
"""

from pydantic import BaseModel, Field
from typing import Optional
from aegis.schemas.agent import TaskRequest, AgentGraphConfig


class LaunchRequest(BaseModel):
    """
    Combines a task with optional execution config and iteration control.
    """

    task: TaskRequest
    config: Optional[AgentGraphConfig] = None
    iterations: Optional[int] = Field(
        default=1, description="Number of planning/execution cycles"
    )
