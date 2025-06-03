"""
Schema exports for API and agent interoperability.

Provides re-exported Pydantic models used across AEGIS for tasks,
configuration, tool metadata, and API IO schemas.
"""

from aegis.schemas.agent import TaskRequest, PresetEntry, AgentGraphConfig
from aegis.schemas.config import ConfigProfile
from aegis.schemas.http import APITaskRequest, APIResponse
from aegis.schemas.machine import MachineManifest
from aegis.schemas.tool import ToolInputMetadata

__all__ = [
    "TaskRequest",
    "PresetEntry",
    "AgentGraphConfig",
    "MachineManifest",
    "ToolInputMetadata",
    "ConfigProfile",
    "APITaskRequest",
    "APIResponse",
]
