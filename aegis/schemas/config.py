# aegis/schemas/config.py
"""
Schemas for profile-based agent configuration, including execution behavior,
graph topology, and default constraints.
"""

from pydantic import BaseModel


class NodeConfig(BaseModel):
    """Represents a node within the agent execution graph.

    :ivar id: Unique node identifier. This is used to reference the node in edges.
    :vartype id: str
    :ivar tool: The name of the agent step function to execute for this node.
               This must match a key in the `AGENT_NODE_REGISTRY`.
    :vartype tool: str
    """

    id: str
    tool: str
