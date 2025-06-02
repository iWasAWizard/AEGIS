"""
Schemas related to agent task requests, presets, and graph configuration.
"""

from typing import List, Dict, Optional, Tuple, Any

from pydantic import BaseModel, Field


class PresetEntry(BaseModel):
    """
    Represents a named preset task.
    """

    name: str
    prompt: str


class TaskRequest(BaseModel):
    """
    Defines a structured task for the agent to execute.
    """

    task_name: str
    task_prompt: str
    machines: List[str] = Field(default_factory=list)
    profile: Optional[str] = None


class AgentGraphConfig(BaseModel):
    """
    Configuration container for building a LangGraph AgentGraph.
    """

    state_type: Any
    entrypoint: str
    edges: List[Tuple[str, str]]
    condition_node: Optional[str] = None
    condition_map: Optional[Dict[str, str]] = None
    middleware: Optional[List[Any]] = None
