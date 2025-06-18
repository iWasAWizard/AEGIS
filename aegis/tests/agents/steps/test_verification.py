# aegis/tests/agents/steps/test_verification.py
"""
Unit tests for the agent's verification and remediation steps.
"""
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from pydantic import BaseModel

from aegis.agents.steps.verification import verify_outcome, remediate_plan
from aegis.agents.task_state import TaskState, HistoryEntry
from aegis.exceptions import ToolError, PlannerError
from aegis.schemas.plan_output import AgentScratchpad
from aegis.schemas.runtime import RuntimeExecutionConfig


class DummyInput(BaseModel):
    pass


@pytest.fixture
def mock_state_factory():
    """Factory to create TaskState objects for tests."""

    def _factory(last_plan: AgentScratchpad, last_observation: str, status: str = "success") -> TaskState:
        entry = HistoryEntry(plan=last_plan, observation=last_observation, status=status)
        return TaskState(
            task_id="test",
            task_prompt="test",
            runtime=RuntimeExecutionConfig(),
            latest_plan=last_plan,
            history=[entry]
        )

    return _factory


@pytest.mark.asyncio
async def test_verify_outcome_no_verification_needed(mock_state_factory):
    """Test that it returns 'success' if no verification tool is specified."""
    plan = AgentScratchpad(thought="test", tool_name="some_tool", tool_args={})
    state = mock_state_factory(plan, "some output")
    result = await verify_outcome(state)
    assert result == "success"


@pytest.mark.asyncio
async def test_verify_outcome_main_tool_failed(mock_state_factory):
    """Test that it returns 'failure' if the main tool's observation was an error."""
    plan = AgentScratchpad(thought="test", tool_name="some_tool", tool_args={})
    state = mock_state_factory(plan, "[ERROR] Main tool failed", status="failure")
    result = await verify_outcome(state)
    assert result == "failure"


@pytest.mark.asyncio
@patch("aegis.agents.steps.verification._run_tool")
@patch("aegis.agents.steps.verification.get_tool")
async def test_verify_outcome_verification_succeeds(mock_get_tool, mock_run_tool, mock_state_factory):
    """Test successful verification when the output contains a success keyword."""
    mock_get_tool.return_value = MagicMock(run=MagicMock(), input_model=DummyInput)
    mock_run_tool.return_value = "Service is active and running."

    plan = AgentScratchpad(thought="t", tool_name="t", verification_tool_name="v_tool")
    state = mock_state_factory(plan, "main output")

    result = await verify_outcome(state)
    assert result == "success"
    mock_run_tool.assert_called_once()


@pytest.mark.asyncio
@patch("aegis.agents.steps.verification._run_tool")
@patch("aegis.agents.steps.verification.get_tool")
async def test_verify_outcome_verification_fails(mock_get_tool, mock_run_tool, mock_state_factory):
    """Test failed verification when the output lacks success keywords."""
    mock_get_tool.return_value = MagicMock(run=MagicMock(), input_model=DummyInput)
    mock_run_tool.return_value = "Service is stopped."

    plan = AgentScratchpad(thought="t", tool_name="t", verification_tool_name="v_tool")
    state = mock_state_factory(plan, "main output")

    result = await verify_outcome(state)
    assert result == "failure"


@pytest.mark.asyncio
@patch("aegis.agents.steps.verification.get_tool")
async def test_verify_outcome_tool_error(mock_get_tool, mock_state_factory):
    """Test that it returns 'failure' if the verification tool itself errors out."""
    mock_get_tool.side_effect = ToolError("Verification tool failed")

    plan = AgentScratchpad(thought="t", tool_name="t", verification_tool_name="v_tool")
    state = mock_state_factory(plan, "main output")

    result = await verify_outcome(state)
    assert result == "failure"


@pytest.mark.asyncio
async def test_remediate_plan_success(mock_state_factory):
    """Test that a remediation plan is generated correctly."""
    mock_llm_query = AsyncMock()
    new_plan_json = '{"thought": "remediation thought", "tool_name": "fix_tool", "tool_args": {}}'
    mock_llm_query.return_value = new_plan_json

    plan = AgentScratchpad(thought="original plan", tool_name="failing_tool")
    state = mock_state_factory(plan, "[ERROR] It failed", status="failure")

    result_dict = await remediate_plan(state, mock_llm_query)

    mock_llm_query.assert_awaited_once()
    # Check that the remediation context was included in the prompt
    assert "Your previous attempt to achieve the goal failed" in mock_llm_query.call_args[0][1]
    assert "remediation thought" in result_dict["latest_plan"].thought


@pytest.mark.asyncio
async def test_remediate_plan_bad_llm_output(mock_state_factory):
    """Test that a PlannerError is raised if the LLM gives bad JSON."""
    mock_llm_query = AsyncMock(return_value="this is not json")

    plan = AgentScratchpad(thought="original plan", tool_name="failing_tool")
    state = mock_state_factory(plan, "[ERROR] It failed", status="failure")

    with pytest.raises(PlannerError):
        await remediate_plan(state, mock_llm_query)
