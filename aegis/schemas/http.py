"""
Schemas for FastAPI HTTP request/response payloads.
"""

from typing import Optional, Dict

from pydantic import BaseModel


class APITaskRequest(BaseModel):
    """
    Request body for launching a task from the web UI.
    """

    task_name: str
    task_prompt: str
    machines: Optional[list[str]] = None
    profile: Optional[str] = None


class APIResponse(BaseModel):
    """
    Represents the APIResponse class.

    Used to return standardized results from web API endpoints, including errors and payloads.
    """

    status: str
    result: Optional[Dict] = None
    error: Optional[str] = None
