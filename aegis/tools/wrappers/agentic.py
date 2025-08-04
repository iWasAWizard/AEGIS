# aegis/tools/wrappers/agentic.py
"""
Wrapper tools for agent-to-agent communication, delegation, and meta-actions.
"""
import json

import httpx
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class DispatchSubtaskInput(BaseModel):
    """Input for dispatching a sub-task to another specialized agent.

    :ivar prompt: The natural language prompt for the sub-task.
    :vartype prompt: str
    :ivar preset: The agent preset to use for the sub-task (e.g., 'default', 'verified_flow').
    :vartype preset: str
    :ivar backend_profile: The backend profile for the sub-agent to use.
    :vartype backend_profile: str
    """

    prompt: str = Field(
        ..., description="The natural language prompt for the sub-task."
    )
    preset: str = Field(
        "default",
        description="The agent preset to use for the sub-task (e.g., 'default', 'verified_flow').",
    )
    backend_profile: str = Field(
        ..., description="The backend profile for the sub-agent to use."
    )


@register_tool(
    name="dispatch_subtask_to_agent",
    input_model=DispatchSubtaskInput,
    description="Delegates a specific, self-contained sub-task to a specialized agent and returns its final summary. Use this for complex tasks that can be broken down.",
    category="agentic",
    tags=["agent", "delegation", "subtask", "wrapper"],
    safe_mode=True,  # The tool itself is safe; safety of the sub-task is governed by its own context.
    purpose="Delegate a complex sub-task to a specialist agent.",
)
async def dispatch_subtask_to_agent(input_data: DispatchSubtaskInput) -> str:
    """
    Invokes another AEGIS agent via the API to perform a sub-task.
    """
    logger.info(
        f"Dispatching sub-task to agent with preset '{input_data.preset}': '{input_data.prompt[:50]}...'"
    )
    launch_url = "http://localhost:8000/api/launch"
    payload = {
        "task": {"prompt": input_data.prompt},
        "config": input_data.preset,
        "execution": {"backend_profile": input_data.backend_profile},
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(launch_url, json=payload, timeout=900)
            response.raise_for_status()
            result = response.json()
            summary = result.get("summary", "Sub-agent did not provide a summary.")
            logger.info(
                f"Sub-task completed successfully. Returning summary to orchestrator."
            )
            return summary
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("detail", e.response.text)
        logger.error(f"Sub-agent task failed with HTTP error: {error_detail}")
        raise ToolExecutionError(f"Sub-agent task failed: {error_detail}")
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to the AEGIS API for sub-task: {e}")
        raise ToolExecutionError(
            f"Could not dispatch sub-task due to a network error: {e}"
        )


class ReviseGoalInput(BaseModel):
    """Input for revising the agent's main goal.

    :ivar new_goal: The new, revised goal for the agent to follow.
    :vartype new_goal: str
    :ivar reason: A justification for why the goal is being changed.
    :vartype reason: str
    """

    new_goal: str = Field(
        ..., description="The new, revised goal for the agent to follow."
    )
    reason: str = Field(
        ..., description="A justification for why the goal is being changed."
    )


@register_tool(
    name="revise_goal",
    input_model=ReviseGoalInput,
    description="Revises the original task prompt if it is found to be flawed, impossible, or suboptimal. Use this to self-correct your high-level objective.",
    category="agentic",
    tags=["agent", "planning", "meta"],
    safe_mode=True,
    purpose="Revise the current main goal to a new one.",
)
def revise_goal(input_data: ReviseGoalInput) -> str:
    """
    Signals the execution step to modify the agent's main goal in the TaskState.
    """
    return f"Goal successfully revised. New goal is: '{input_data.new_goal}'"


class AdvanceToNextSubGoalInput(BaseModel):
    """Input for advancing to the next sub-goal. Takes no arguments."""

    pass


@register_tool(
    name="advance_to_next_sub_goal",
    input_model=AdvanceToNextSubGoalInput,
    description="Marks the current sub-goal as complete and advances the focus to the next sub-goal in the high-level plan. Call this ONLY when the current sub-goal is fully achieved.",
    category="agentic",
    tags=["agent", "planning", "meta", "sub-goal"],
    safe_mode=True,
    purpose="Advance to the next sub-goal in the plan.",
)
def advance_to_next_sub_goal(input_data: AdvanceToNextSubGoalInput) -> str:
    """
    Signals the execution step to increment the sub-goal index in the TaskState.
    """
    return "Successfully advanced to the next sub-goal."
