"""
Schemas for tool input/output models and registry metadata.
"""

from typing import List, Optional, Type

from pydantic import BaseModel


class ToolInputMetadata(BaseModel):
    """
    Metadata for a registered tool's expected input.
    """

    name: str
    input_model: Type[BaseModel]
    tags: List[str]
    description: str
    safe_mode: bool = True
    purpose: Optional[str] = None
    category: Optional[str] = None
    timeout: Optional[int] = None
    retries: int = 0
