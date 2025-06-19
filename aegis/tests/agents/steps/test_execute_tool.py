# aegis/tests/agents/steps/test_execute_tool.py
"""
Tests for the core tool execution agent step.
"""
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from aegis.agents.steps.execute_tool import execute_tool
from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolNotFoundError
from aegis.schemas.plan_output import AgentScratchpad
from aegis.schemas.runtime import RuntimeExecutionConfig


class MockInput(BaseModel):
    arg: str


@pytest.fixture
def mock_tool_registry(monkeypatch):
    """Mocks the get_tool function in the registry."""
    mock_get = MagicMock()
    monkeypatch.setattr("aegis.agents.steps.execute_tool.get_tool", mock_get)
    return mock_get


@pytest.mark.asyncio
async def test_execute_tool_success(mock_tool_registry):
    """Verify a successful tool execution creates a correct HistoryEntry."""
    # Setup mock tool
    mock_run = MagicMock(return_value="tool success output")
    mock_tool_entry = MagicMock(run=mock_run, input_model=MockInput)
    mock_tool_registry.return_value = mock_tool_entry

    plan = AgentScratchpad(
        thought="run tool", tool_name="mock_tool", tool_args={"arg": "test"}
    )
    state = TaskState(
        task_id="t1",
        task_prompt="p",
        runtime=RuntimeExecutionConfig(),
        latest_plan=plan,
    )

    result_dict = await execute_tool(state)

    assert "history" in result_dict
    history = result_dict["history"]
    assert len(history) == 1

    entry = history[0]
    assert entry.status == "success"
    assert entry.observation == "tool success output"
    assert entry.plan == plan
    assert entry.duration_ms > 0


@pytest.mark.asyncio
async def test_execute_tool_failure(mock_tool_registry):
    """Verify a failed tool execution creates a correct HistoryEntry."""
    mock_tool_registry.side_effect = ToolNotFoundError("Tool does not exist")

    plan = AgentScratchpad(thought="run bad tool", tool_name="bad_tool", tool_args={})
    state = TaskState(
        task_id="t2",
        task_prompt="p",
        runtime=RuntimeExecutionConfig(),
        latest_plan=plan,
    )

    result_dict = await execute_tool(state)

    entry = result_dict["history"][0]
    assert entry.status == "failure"
    assert "[ERROR] Tool lookup failed" in entry.observation
    assert "Tool does not exist" in entry.observation


@pytest.mark.asyncio
async def test_execute_tool_no_plan():
    """Verify that a HistoryEntry is still created even if the state has no plan."""
    state = TaskState(
        task_id="t3",
        task_prompt="p",
        runtime=RuntimeExecutionConfig(),
        latest_plan=None,
    )
    result_dict = await execute_tool(state)

    entry = result_dict["history"][0]
    assert entry.status == "failure"
    assert "No plan found in state" in entry.observation
