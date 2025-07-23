# aegis/tests/agents/steps/test_verification.py
"""
Unit tests for the agent's verification and remediation steps.
"""
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from pydantic import BaseModel

from aegis.agents.steps.verification import verify_outcome, remediate_plan, VerificationJudgement
from aegis.agents.task_state import TaskState, HistoryEntry
from aegis.exceptions import ToolError, PlannerError
from aegis.schemas.plan_output import AgentScratchpad
from aegis.schemas.runtime import RuntimeExecutionConfig


class DummyInput(BaseModel):
    pass


@pytest.fixture
def mock_state_factory():
    """Factory to create TaskState objects for tests."""

    def _factory(
        last_plan: AgentScratchpad, last_observation: str, status: str = "success"
    ) -> TaskState:
        entry = HistoryEntry(
            plan=last_plan, observation=last_observation, status=status
        )
        return TaskState(
            task_id="test",
            task_prompt="test",
            runtime=RuntimeExecutionConfig(backend_profile="test"),
            latest_plan=last_plan,
            history=[entry],
        )

    return _factory


@pytest.fixture
def mock_instructor_client(monkeypatch):
    """Mocks the instructor-patched OpenAI client for both verify and remediate."""
    mock_create = AsyncMock()
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create
    monkeypatch.setattr("aegis.agents.steps.verification.instructor.patch", lambda x: mock_client)
    monkeypatch.setattr("aegis.agents.steps.verification.OpenAI", MagicMock())
    monkeypatch.setattr("aegis.agents.steps.verification.get_backend_config", MagicMock(return_value=MagicMock(llm_url="http://test/v1/c", model="test")))
    return mock_create


@pytest.mark.asyncio
async def test_verify_outcome_no_verification_needed(mock_state_factory):
    """Test that it assumes 'success' if no verification tool is specified."""
    plan = AgentScratchpad(thought="test", tool_name="some_tool", tool_args={})
    state = mock_state_factory(plan, "some output")
    result = await verify_outcome(state)
    assert result["history"][-1].verification_status == "success"


@pytest.mark.asyncio
async def test_verify_outcome_main_tool_failed(mock_state_factory):
    """Test that it automatically fails if the main tool's status was 'failure'."""
    plan = AgentScratchpad(thought="test", tool_name="some_tool", tool_args={})
    state = mock_state_factory(plan, "[ERROR] Main tool failed", status="failure")
    result = await verify_outcome(state)
    assert result["history"][-1].verification_status == "failure"


@pytest.mark.asyncio
@patch("aegis.agents.steps.verification._run_tool")
@patch("aegis.agents.steps.verification.get_tool")
async def test_verify_outcome_verification_succeeds(
    mock_get_tool, mock_run_tool, mock_state_factory, mock_instructor_client
):
    """Test successful verification when the LLM judge returns 'success'."""
    mock_get_tool.return_value = MagicMock(run=MagicMock(), input_model=DummyInput)
    mock_run_tool.return_value = "Service is active and running."
    mock_instructor_client.return_value = VerificationJudgement(judgement="success")

    plan = AgentScratchpad(thought="t", tool_name="t", verification_tool_name="v_tool")
    state = mock_state_factory(plan, "main output")

    result = await verify_outcome(state)
    assert result["history"][-1].verification_status == "success"


@pytest.mark.asyncio
async def test_remediate_plan_success(mock_state_factory, mock_instructor_client):
    """Test that a remediation plan is generated correctly."""
    new_plan = AgentScratchpad(thought="remediation thought", tool_name="fix_tool", tool_args={})
    mock_instructor_client.return_value = new_plan

    plan = AgentScratchpad(thought="original plan", tool_name="failing_tool")
    state = mock_state_factory(plan, "[ERROR] It failed", status="failure")

    result_dict = await remediate_plan(state)

    mock_instructor_client.assert_awaited_once()
    assert "remediation thought" in result_dict["latest_plan"].thought