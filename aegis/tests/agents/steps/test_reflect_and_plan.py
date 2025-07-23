# aegis/tests/agents/steps/test_reflect_and_plan.py
"""
Unit tests for the reflect_and_plan agent step.
"""
from unittest.mock import AsyncMock, patch

import pytest

from aegis.agents.steps.reflect_and_plan import (
    reflect_and_plan,
    construct_planning_prompt,
)
from aegis.agents.task_state import TaskState, HistoryEntry
from aegis.exceptions import PlannerError
from aegis.schemas.plan_output import AgentScratchpad
from aegis.schemas.runtime import RuntimeExecutionConfig


@pytest.fixture
def populated_state() -> TaskState:
    """Provides a TaskState with a history of one step."""
    plan = AgentScratchpad(
        thought="Initial thought", tool_name="initial_tool", tool_args={}
    )
    entry = HistoryEntry(plan=plan, observation="Initial observation", status="success")
    return TaskState(
        task_id="plan-test",
        task_prompt="This is the main goal.",
        runtime=RuntimeExecutionConfig(backend_profile="test_backend"),
        history=[entry],
    )


@pytest.fixture
def mock_instructor_client(monkeypatch):
    """Mocks the instructor-patched OpenAI client."""
    mock_create = AsyncMock()
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create = mock_create
    monkeypatch.setattr("instructor.patch", lambda x: mock_client_instance)
    monkeypatch.setattr("openai.OpenAI", MagicMock())
    monkeypatch.setattr("aegis.agents.steps.reflect_and_plan.get_backend_config", MagicMock(return_value=MagicMock(llm_url="http://test/v1/c", model="test")))
    return mock_create


def test_construct_planning_prompt(populated_state):
    """Verify that the planning prompt is constructed correctly with all sections."""
    system_prompt, user_prompt = construct_planning_prompt(populated_state)

    # Test system prompt
    assert "You are an autonomous agent" in system_prompt
    assert "## Available Tools" in system_prompt
    assert (
        "finish(reason: string, status: string)" in system_prompt
    )  # Check for a known tool

    # Test user prompt
    assert "## Main Goal" in user_prompt
    assert "This is the main goal." in user_prompt
    assert "## Previous Steps" in user_prompt
    assert "Thought: Initial thought" in user_prompt
    assert "Observation: Initial observation" in user_prompt


@pytest.mark.asyncio
async def test_reflect_and_plan_success(mock_instructor_client):
    """Verify the step correctly parses a valid LLM response."""
    valid_plan = AgentScratchpad(thought="test thought", tool_name="test_tool", tool_args={"a": 1})
    mock_instructor_client.return_value = valid_plan

    state = TaskState(task_id="t1", task_prompt="p", runtime=RuntimeExecutionConfig(backend_profile="test"))

    result_dict = await reflect_and_plan(state)

    mock_instructor_client.assert_awaited_once()
    assert "latest_plan" in result_dict
    plan = result_dict["latest_plan"]
    assert isinstance(plan, AgentScratchpad)
    assert plan.thought == "test thought"
    assert plan.tool_name == "test_tool"


@pytest.mark.asyncio
async def test_reflect_and_plan_raises_planner_error_on_bad_json(mock_instructor_client):
    """Verify the step raises a PlannerError if the LLM response is not valid JSON."""
    mock_instructor_client.side_effect = PlannerError("LLM failed to produce valid JSON")
    state = TaskState(task_id="t2", task_prompt="p", runtime=RuntimeExecutionConfig(backend_profile="test"))

    with pytest.raises(PlannerError):
        await reflect_and_plan(state)