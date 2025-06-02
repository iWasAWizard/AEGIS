"""
Schemas for runtime configuration profiles and loading behavior.
"""

from typing import Any, List, Tuple, Dict
from typing import Optional

from pydantic import BaseModel


class ConfigProfile(BaseModel):
    """
    Represents the ConfigProfile class.

    Use this class to define a set of configuration parameters for agent execution profiles.
    """

    default_profile: Optional[str] = None
    timeout_override: Optional[int] = None
    safe_mode_default: Optional[bool] = True


class AgentConfig(BaseModel):
    """
    Configuration model for building an agent task graph.
    """

    state_type: Any
    entrypoint: str
    edges: List[Tuple[str, str]]
    condition_node: Optional[str] = None
    condition_map: Optional[Dict[str, str]] = None
    middleware: Optional[List[Any]] = None
