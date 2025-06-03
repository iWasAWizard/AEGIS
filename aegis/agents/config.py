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
    edges=[
        ("reflect_and_plan", "execute_tool"),
        ("execute_tool", "route_after_tool"),
        ("route_after_tool", "reflect_and_plan"),
        ("route_after_tool", "summarize_result"),
        ("reflect_and_plan", "summarize_result"),
        ("summarize_result", "check_termination"),
        ("check_termination", END),
    ],
    nodes=[
        NodeConfig(id="reflect_and_plan", tool="reflect_and_plan"),
        NodeConfig(id="execute_tool", tool="execute_tool"),
        NodeConfig(id="route_after_tool", tool=None),
        NodeConfig(id="summarize_result", tool="summarize_result"),
        NodeConfig(id="check_termination", tool="check_termination"),
    ],
    condition_node="route_after_tool",
    condition_map={
        "run": "execute_tool",
        "execute": "execute_tool",
        "execute_tool": "execute_tool",
        "use": "execute_tool",
        "manipulate": "execute_tool",
        "rerun": "execute_tool",
        "retry": "execute_tool",
        "reflect_and_plan": "reflect_and_plan",
        "plan": "reflect_and_plan",
        "reflect": "reflect_and_plan",
        "replan": "reflect_and_plan",
        "continue": "reflect_and_plan",
        "summarize_result": "summarize_result",
        "summarize": "summarize_result",
        "stop": "check_termination",
        "end": "check_termination",
        "complete": "check_termination",
    },
    middleware=[],
)
