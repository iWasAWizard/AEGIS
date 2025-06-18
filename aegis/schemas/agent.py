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
    :vartype state_type: Any
    :ivar entrypoint: The ID of the first node to be executed in the graph.
    :vartype entrypoint: str
    :ivar nodes: A list of all node configurations that make up the graph.
    :vartype nodes: List[NodeConfig]
    :ivar edges: A list of tuples defining unconditional transitions between nodes.
    :vartype edges: List[Tuple[str, str]]
    :ivar condition_node: The ID of the node whose output determines conditional routing.
    :vartype condition_node: Optional[str]
    :ivar condition_map: A dictionary mapping an output key to a destination node ID.
    :vartype condition_map: Dict[str, str]
    :ivar middleware: An optional list of callables to modify state during execution.
    :vartype middleware: Optional[List[Callable[[Dict], Dict]]]
    """

    state_type: Any
    entrypoint: str
    nodes: List[NodeConfig] = Field(default_factory=list)
    edges: List[Tuple[str, str]] = Field(default_factory=list)
    condition_node: Optional[str] = None
    condition_map: Dict[str, str] = Field(default_factory=dict)
    middleware: Optional[List[Callable[[Dict], Dict]]] = None

    class Config:
        """Pydantic configuration to allow arbitrary types like callables."""

        arbitrary_types_allowed = True


class AgentConfig(BaseModel):
    """Represents a high-level, user-facing agent configuration preset.

    This model is a more flexible version of AgentGraphConfig, allowing for
    optional fields. It's used for initial parsing from sources like YAML
    presets before being promoted to a full AgentGraphConfig.

    :ivar state_type: The state class reference (can be a string for dynamic import).
    :vartype state_type: Optional[Any]
    :ivar entrypoint: The ID of the entry node.
    :vartype entrypoint: Optional[str]
    :ivar nodes: A list of all node configurations that make up the graph.
    :vartype nodes: List[NodeConfig]
    :ivar edges: List of unconditional graph edges.
    :vartype edges: List[Tuple[str, str]]
    :ivar condition_node: The node used for conditional routing.
    :vartype condition_node: Optional[str]
    :ivar condition_map: The mapping for conditional routing.
    :vartype condition_map: Dict[str, str]
    :ivar middleware: Optional list of middleware callables.
    :vartype middleware: Optional[List[Any]]
    :ivar runtime: Default runtime options for this agent configuration.
    :vartype runtime: RuntimeExecutionConfig
    """

    state_type: Optional[Any] = None
    entrypoint: Optional[str] = None
    nodes: List[NodeConfig] = Field(default_factory=list)
    edges: List[Tuple[str, str]] = Field(default_factory=list)
    condition_node: Optional[str] = None
    condition_map: Dict[str, str] = Field(default_factory=dict)
    middleware: Optional[List[Any]] = None
    runtime: RuntimeExecutionConfig = Field(default_factory=RuntimeExecutionConfig)

    class Config:
        """Pydantic configuration to allow arbitrary types like callables."""

        arbitrary_types_allowed = True


class PresetEntry(BaseModel):
    """Represents a single named preset in a configuration file.

    :ivar name: The user-friendly name of the preset.
    :vartype name: str
    :ivar config: The AgentConfig associated with this preset.
    :vartype config: AgentConfig
    """

    name: str
    config: AgentConfig
