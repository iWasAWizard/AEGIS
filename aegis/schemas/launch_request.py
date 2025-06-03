"""
Schema for launching a task with custom config and runtime options.
"""

from pydantic import BaseModel, Field
from typing import Optional
from aegis.schemas.agent import TaskRequest
from aegis.schemas.runtime_execution_config import RuntimeExecutionConfig


class LaunchRequest(BaseModel):
    """
    Combines a task with optional execution config and iteration control.
    """

    task: TaskRequest
    config: Optional[RuntimeExecutionConfig] = Field(
        default_factory=RuntimeExecutionConfig,
        description="Client-controlled runtime settings like model name and LLM URL",
    )
    iterations: Optional[int] = Field(
        default=1, description="Number of planning/execution cycles"
    )
