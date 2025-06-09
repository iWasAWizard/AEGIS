# aegis/schemas/common_inputs.py
"""
Pydantic models for common tool inputs used across the framework.

Defining these base models here allows for consistent input structures
and reduces code duplication in the tool definition files. Tools that operate
on machines or remote files should inherit from these models.
"""
from pydantic import BaseModel, Field


class MachineTargetInput(BaseModel):
    """A base model for any tool that targets a machine from machines.yaml.

    :ivar machine_name: The name of the target machine as defined in machines.yaml.
    :vartype machine_name: str
    """

    machine_name: str = Field(
        ..., description="The name of the target machine as defined in machines.yaml."
    )


class MachineFileInput(MachineTargetInput):
    """Input model for tools that operate on a specific file on a target machine.

    :ivar file_path: The absolute path to the file on the remote system.
    :vartype file_path: str
    """

    file_path: str = Field(
        ..., description="The absolute path to the file on the remote system."
    )


class MachineUserInput(MachineTargetInput):
    """Input model for tools that manage a specific user on a target machine.

    :ivar username: The target username on the remote system.
    :vartype username: str
    """

    username: str = Field(..., description="The target username on the remote system.")
