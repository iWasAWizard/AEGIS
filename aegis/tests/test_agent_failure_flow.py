# aegis/tests/test_agent_failure_flow.py
"""
End-to-end integration test for agent failure and recovery flow.
"""
import json
from unittest.mock import MagicMock

import pytest

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolExecutionError
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.runtime import RuntimeExecutionConfig


@pytest.fixture
def mock_llm_for_failure(monkeypatch):
    """Mocks the LLM to first try a failing command, then finish."""
    plan_fail = {
        "thought": "I will try a command that I know will fail.",
        "tool_name": "run_local_command",
        "tool_args": {"command": "command_that_will_fail"},
    }
    plan_recover = {
        "thought": "The previous command failed as expected. I will now finish the task.",
        "tool_name": "finish",
        "tool_args": {"reason": "Recovered from tool failure.", "status": "partial"},
    }
    mock = MagicMock(side_effect=[json.dumps(plan_fail), json.dumps(plan_recover)])

    async def async_mock(*_args, **_kwargs):
        return mock()

    monkeypatch.setattr("aegis.utils.llm_query.llm_query", async_mock)
    return mock


@pytest.fixture
def mock_failing_command(monkeypatch):
    """Mocks the run_local_command tool to raise a ToolExecutionError."""
    mock = MagicMock(side_effect=ToolExecutionError("Tool failed intentionally!"))
    monkeypatch.setattr("aegis.agents.steps.execute_tool._run_tool", mock)
    return mock


@pytest.mark.asyncio
async def test_agent_recovers_from_tool_failure(
    mock_llm_for_failure, mock_failing_command
):
    """
    Tests that the agent can:
    1. Attempt to run a tool that fails.
    2. Record the failure in its history.
    3. Loop back to the planning step.
    4. See the failure in its prompt and make a new plan to recover.
    """
    from aegis.utils.config_loader import load_agent_config

    config: AgentConfig = load_agent_config(
        profile="verified_flow"
    )  # Use the flow that can remediate
    agent_graph = AgentGraph(AgentGraphConfig(**config.model_dump())).build_graph()
    initial_state = TaskState(
        task_id="test-fail-flow-123",
        task_prompt="Run a command that fails, then finish.",
        runtime=RuntimeExecutionConfig(iterations=5),
    )

    final_state_dict = await agent_graph.ainvoke(initial_state.model_dump())
    final_state = TaskState(**final_state_dict)

    assert mock_llm_for_failure.call_count == 2
    mock_failing_command.assert_called_once()
    assert len(final_state.history) == 2

    _plan, observation = final_state.history[0]
    assert isinstance(observation, str)
    assert "[ERROR]" in observation
    assert "ToolExecutionError" in observation
    assert "Tool failed intentionally!" in observation

    assert final_state.history[1][0].tool_name == "finish"
