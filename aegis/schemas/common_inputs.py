# aegis/schemas/common_inputs.py
"""
Pydantic models for common tool inputs used across the framework.

Defining these base models here allows for consistent input structures
and reduces code duplication in the tool definition files.
"""
from typing import Optional
from pydantic import BaseModel, Field


class RemoteTargetInput(BaseModel):
    """A base model for any tool that targets a remote host via SSH."""

    host: str = Field(..., description="Remote host in 'user@host.com' format.")
    ssh_key_path: Optional[str] = Field(
        None, description="Optional path to the SSH private key."
    )


class RemoteFileInput(RemoteTargetInput):
    """Input model for tools that operate on a specific file on a remote host."""

    file_path: str = Field(
        ..., description="The absolute path to the file on the remote system."
    )


class RemoteUserInput(RemoteTargetInput):
    """Input model for tools that manage a specific user on a remote host."""

    username: str = Field(..., description="The target username on the remote system.")
