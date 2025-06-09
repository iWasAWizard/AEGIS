# aegis/schemas/launch.py
"""
Pydantic schema for a complete agent launch request.

This module contains the `LaunchRequest` model, which acts as a comprehensive
"envelope" for initiating an agent task. It combines the core `TaskRequest`
with all necessary configuration for the agent graph and runtime behavior,
making it the primary data structure for the `/launch` API endpoint.
"""

from typing import Optional, Union, Dict, Any

from pydantic import BaseModel, Field

from aegis.schemas.agent import AgentConfig
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.schemas.task import TaskRequest


class LaunchRequest(BaseModel):
    """Represents a complete and fully configured agent execution request.

    This schema wraps a `TaskRequest` with optional configuration parameters
    to control the agent's graph, runtime behavior, and execution limits. It
    is designed to be the payload for the main `/launch` API endpoint.

    :ivar task: The core task definition, including the user's prompt.
    :ivar config: The agent graph configuration. Can be a profile name (str),
                  a raw dictionary, or an `AgentConfig` object.
    :ivar execution: Optional runtime overrides for this specific launch.
    :ivar iterations: A specific override for the maximum number of agent steps.
    """
    task: TaskRequest = Field(..., description="The task prompt and metadata.")
    config: Union[str, Dict[str, Any], AgentConfig] = Field(
        default="default",
        description="The agent graph configuration to use, specified as a profile name, dict, or object.",
    )
    execution: Optional[RuntimeExecutionConfig] = Field(
        default=None,
        description="Optional runtime execution overrides for this launch.",
    )
    iterations: Optional[int] = Field(
        default=None,
        description="A specific override for the maximum number of agent planning iterations.",
    )
