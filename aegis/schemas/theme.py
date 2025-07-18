# aegis/schemas/theme.py
"""
Pydantic schemas for defining UI theme configurations.
"""
from typing import Dict
from pydantic import BaseModel, Field


class ThemeConfig(BaseModel):
    """
    Validates the structure of a theme YAML file.
    """

    name: str = Field(..., description="The display name of the theme.")
    description: str = Field(..., description="A short description of the theme.")
    properties: Dict[str, str] = Field(
        ..., description="A dictionary of CSS variable key-value pairs."
    )
