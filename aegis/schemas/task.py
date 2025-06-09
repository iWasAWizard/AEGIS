# aegis/schemas/task.py
"""
Pydantic schema for defining a user-initiated task request.

This module contains the `TaskRequest` model, which serves as the primary
input structure for launching a new agent task. It captures the user's
natural language prompt and any associated metadata.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """Represents a natural language prompt and its metadata from a user.

    This schema defines the initial input that the agent receives. It is
    typically created from a CLI command, an API call, or a UI form submission.

    :ivar prompt: The natural language instruction for the agent.
    :vartype prompt: str
    :ivar task_id: An optional unique identifier for tracking the task.
    :vartype task_id: Optional[str]
    :ivar model: An optional override for the LLM model to be used for this specific task.
    :vartype model: Optional[str]
    """

    prompt: str = Field(..., description="Natural language input to the agent.")
    task_id: Optional[str] = Field(
        default=None,
        description="Optional unique identifier for the task.",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional override for model used in execution.",
    )
