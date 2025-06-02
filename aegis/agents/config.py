from dataclasses import dataclass
from typing import Any, List, Tuple, Dict, Optional

from langgraph.graph import END

from aegis.agents.task_state import TaskState


@dataclass
class NodeConfig:
    """
    Represents the NodeConfig class.

    Defines configuration options for a single node in the agent graph.
    """

    id: str
    tool: Optional[str] = None


@dataclass
class AgentGraphConfig:
    """
    Represents the AgentGraphConfig class.

    Encapsulates all settings for constructing an AgentGraph, including node definitions and routing behaviors.
    """

    state_type: Any
    entrypoint: str
    edges: List[Tuple[str, str]]
    condition_node: Optional[str]
    condition_map: Optional[Dict[str, str]]
    nodes: List[NodeConfig]
    middleware: Optional[Any] = None


graph_config = AgentGraphConfig(
    state_type=TaskState,
    entrypoint="reflect_and_plan",
    edges=[("reflect_and_plan", "run_tool"), ("run_tool", "route_after_tool")],
    nodes=[
        NodeConfig(id="reflect_and_plan", tool="reflect_and_plan"),
        NodeConfig(id="run_tool", tool="run_tool"),
        NodeConfig(id="route_after_tool", tool=None),
    ],
    condition_node="route_after_tool",
    condition_map={
        "replan": "reflect_and_plan",
        "rerun": "run_tool",
        "continue": "reflect_and_plan",
        "end": END,
    },
    middleware=[],
)
