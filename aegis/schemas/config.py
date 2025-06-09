"""
Schemas for profile-based agent configuration, including execution behavior,
graph topology, and default constraints.
"""

from typing import Optional

from pydantic import BaseModel


class ConfigProfile(BaseModel):
    """
    Represents global configuration parameters for an execution profile.

    :param default_profile: Name of the default profile (if any).
    :param timeout_override: Default timeout applied to tools.
    :param safe_mode_default: Whether to enforce safe_mode by default.
    """

    default_profile: Optional[str] = None
    timeout_override: Optional[int] = None
    safe_mode_default: Optional[bool] = True


class NodeConfig(BaseModel):
    """
    Represents a node within the agent execution graph.

    :param id: Unique node identifier.
    :param tool: Optional name of the tool associated with this node.
    """

    id: str
    tool: Optional[str] = None
