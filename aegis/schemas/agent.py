# aegis/schemas/agent.py
"""
Pydantic schemas for defining agent configurations and graph structures.

This module contains the core data structures used to define the behavior,
topology, and runtime parameters of an AEGIS agent. These models are used to
parse preset YAML files and to construct the LangGraph StateGraph.
"""

from typing import Any, Dict, List, Tuple, Optional, Callable

from pydantic import BaseModel, Field

from aegis.schemas.config import NodeConfig
from aegis.schemas.runtime import RuntimeExecutionConfig


class AgentGraphConfig(BaseModel):
    """A fully-defined configuration for an agent execution graph.

    This model represents the complete blueprint needed to construct a LangGraph
    StateGraph. It is the target format that all preset configurations are
    ultimately parsed into.

    :ivar state_type: The class reference for the graph's state (e.g., TaskState).
    :ivar entrypoint: The ID of the first node to be executed in the graph.
    :ivar nodes: A list of all node configurations that make up the graph.
    :ivar edges: A list of tuples defining unconditional transitions between nodes.
    :ivar condition_node: The ID of the node whose output determines conditional routing.
    :ivar condition_map: A dictionary mapping an output key to a destination node ID.
    :ivar middleware: An optional list of callables to modify state during execution.
    """

    state_type: Any
    entrypoint: str
    nodes: List[NodeConfig] = Field(default_factory=list)
    edges: List[Tuple[str, str]] = Field(default_factory=list)
    condition_node: Optional[str] = None
    condition_map: Dict[str, str] = Field(default_factory=dict)
    middleware: Optional[List[Callable[[Dict], Dict]]] = None


class AgentConfig(BaseModel):
    """Represents a high-level, user-facing agent configuration preset.

    This model is a more flexible version of AgentGraphConfig, allowing for
    optional fields. It's used for initial parsing from sources like YAML
    presets before being promoted to a full AgentGraphConfig.

    :ivar state_type: The state class reference (can be a string for dynamic import).
    :ivar entrypoint: The ID of the entry node.
    :ivar nodes: A list of all node configurations that make up the graph.
    :ivar edges: List of unconditional graph edges.
    :ivar condition_node: The node used for conditional routing.
    :ivar condition_map: The mapping for conditional routing.
    :ivar middleware: Optional list of middleware callables.
    :ivar runtime: Default runtime options for this agent configuration.
    """

    state_type: Optional[Any] = None
    entrypoint: Optional[str] = None
    nodes: List[NodeConfig] = Field(default_factory=list)
    edges: List[Tuple[str, str]] = Field(default_factory=list)
    condition_node: Optional[str] = None
    condition_map: Dict[str, str] = Field(default_factory=dict)
    middleware: Optional[List[Any]] = None
    runtime: RuntimeExecutionConfig = Field(default_factory=RuntimeExecutionConfig)


class PresetEntry(BaseModel):
    """Represents a single named preset in a configuration file.

    :ivar name: The user-friendly name of the preset.
    :ivar config: The AgentConfig associated with this preset.
    """

    name: str
    config: AgentConfig
