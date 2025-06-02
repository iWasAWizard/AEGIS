"""
Schemas related to machine manifest declarations.
"""

from typing import List

from pydantic import BaseModel


class MachineManifest(BaseModel):
    """
    Represents a list of allowed machine targets.
    """

    machines: List[str]
