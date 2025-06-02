"""Defines the basic Task model used in agent workflow tracking."""

from typing import Literal

from pydantic import BaseModel


class Task(BaseModel):
    """
    Represents the Task class.

    Defines a unit of work with a unique ID, prompt, and associated metadata for execution.
    """

    id: str
    status: Literal["todo", "in_progress", "done"]
    description: str
