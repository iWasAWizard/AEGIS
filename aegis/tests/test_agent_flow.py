# aegis/tests/test_agent_flow.py
"""
End-to-end integration test for the agent's core control flow.
"""
import json
from unittest.mock import MagicMock

import pytest

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import PlannerError
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.runtime import RuntimeExecutionConfig


@pytest.fixture
def mock_llm_query(monkeypatch):
    """Mocks the llm_query function to return a predictable tool plan."""
    plan1_str = json.dumps({
        "thought": "I need to find the current user. I will use `run_local_command` with `whoami`.",
        "tool_name": "run_local_command",
        "tool_args": {"command": "whoami"},
    })
    plan2_str = json.dumps({
        "thought": "I have successfully found the user. The task is complete.",
        "tool_name": "finish",
        "tool_args": {"reason": "User found.", "status": "success"},
    })

    mock = MagicMock(side_effect=[plan1_str, plan2_str])

    async def async_mock_llm_query(*_args, **_kwargs):
        return mock()

    monkeypatch.setattr("aegis.utils.llm_query.llm_query", async_mock_llm_query)
    return mock


@pytest.fixture
def mock_local_command(monkeypatch):
    """Mocks the run_local_command tool to return a predictable username."""
    mock = MagicMock(return_value="test_user")
    monkeypatch.setattr("aegis.tools.primitives.primitive_system.run_local_command", mock)
    return mock


@pytest.mark.asyncio
async def test_full_agent_run(mock_llm_query, mock_local_command):
    """
    Tests the full agent loop from prompt to final summary on a successful run.
    """
    from aegis.utils.config_loader import load_agent_config
    config: AgentConfig = load_agent_config(profile="default")
    agent_graph = AgentGraph(AgentGraphConfig(**config.model_dump())).build_graph()
    initial_state = TaskState(
        task_id="test-flow-123",
        task_prompt="Who am I?",
        runtime=RuntimeExecutionConfig(iterations=5),
    )

    final_state_dict = await agent_graph.ainvoke(initial_state.model_dump())
    final_state = TaskState(**final_state_dict)

    assert mock_llm_query.call_count == 2
    mock_local_command.assert_called_once()
    call_args = mock_local_command.call_args[0][0]
    assert call_args.command == "whoami"

    assert len(final_state.history) == 2
    assert final_state.history[0].plan.tool_name == "run_local_command"
    assert final_state.history[0].observation == "test_user"
    assert final_state.history[1].plan.tool_name == "finish"

    assert final_state.final_summary is not None
    assert "test_user" in final_state.final_summary
    assert "whoami" in final_state.final_summary


@pytest.mark.asyncio
async def test_full_agent_run_with_planner_error(monkeypatch):
    """
    Tests that the entire agent run fails with a PlannerError if the LLM returns invalid JSON.
    """
    # Mock the LLM to return a non-JSON string
    bad_response = "I am not a JSON object."

    async def async_mock_bad_llm_query(*_args, **_kwargs):
        return bad_response

    monkeypatch.setattr("aegis.utils.llm_query.llm_query", async_mock_bad_llm_query)

    from aegis.utils.config_loader import load_agent_config
    config: AgentConfig = load_agent_config(profile="default")
    agent_graph = AgentGraph(AgentGraphConfig(**config.model_dump())).build_graph()
    initial_state = TaskState(
        task_id="test-planner-fail",
        task_prompt="This task will fail.",
        runtime=RuntimeExecutionConfig(iterations=5),
    )

    # We expect the entire invocation to raise our custom PlannerError
    with pytest.raises(PlannerError, match="LLM returned malformed plan"):
        await agent_graph.ainvoke(initial_state.model_dump())
