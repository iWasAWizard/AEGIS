"""Schema definitions for tool input models used by various system commands."""

from typing import Optional

from pydantic import BaseModel, Field


class RunCommandByNameInput(BaseModel):
    """
    RunCommandByNameInput class.
    """

    command: str = Field(description="Name of the command to run.")


class CommandWithArgsInput(BaseModel):
    """
    CommandWithArgsInput class.
    """

    extra_args: Optional[str] = Field(
        default="", description="Extra arguments to pass to the command."
    )
