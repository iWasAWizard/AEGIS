# aegis/tests/agents/steps/test_summarize_result.py
"""
Unit tests for the summarize_result agent step.
"""
from unittest.mock import patch

import pytest

from aegis.agents.steps.summarize_result import summarize_result
from aegis.agents.task_state import TaskState, HistoryEntry
from aegis.schemas.plan_output import AgentScratchpad
from aegis.schemas.runtime import RuntimeExecutionConfig


@pytest.fixture
def populated_state() -> TaskState:
    """Provides a TaskState with a history of two steps using HistoryEntry."""
    runtime = RuntimeExecutionConfig()
    state = TaskState(
        task_id="summary-test-123", task_prompt="Test summarization", runtime=runtime
    )

    plan1 = AgentScratchpad(
        thought="First step.", tool_name="tool_one", tool_args={"arg": "A"}
    )
    entry1 = HistoryEntry(
        plan=plan1, observation="Output of tool one.", status="success"
    )

    plan2 = AgentScratchpad(
        thought="Second step.", tool_name="tool_two", tool_args={"arg": "B"}
    )
    entry2 = HistoryEntry(
        plan=plan2, observation="Output of tool two.", status="success"
    )

    state.history = [entry1, entry2]
    return state


def test_summarize_with_history(populated_state: TaskState):
    """Verify that a summary is correctly generated from a populated history."""
    result_dict = summarize_result(populated_state)
    summary = result_dict.get("final_summary")

    assert summary is not None
    assert "AEGIS Task Report: summary-test-123" in summary
    assert "Goal:** Test summarization" in summary

    assert "Step 1: tool_one" in summary
    assert "Thought:** First step." in summary
    assert "Output of tool one." in summary

    assert "Step 2: tool_two" in summary
    assert "Thought:** Second step." in summary
    assert "Output of tool two." in summary


def test_summarize_empty_history():
    """Verify that a correct message is returned for a task with no history."""
    runtime = RuntimeExecutionConfig()
    state = TaskState(task_id="empty-test", task_prompt="Do nothing", runtime=runtime)
    result_dict = summarize_result(state)
    summary = result_dict.get("final_summary")
    assert summary == "No actions were taken by the agent."


@patch("aegis.agents.steps.summarize_result.generate_provenance_report")
@patch("aegis.agents.steps.summarize_result.update_memory_index")
def test_summarize_triggers_provenance_and_memory(
    mock_update_memory, mock_gen_provenance, populated_state
):
    """Verify that summarize_result calls the provenance and memory indexer utilities."""
    summarize_result(populated_state)
    mock_gen_provenance.assert_called_once_with(populated_state)
    mock_update_memory.assert_called_once()
