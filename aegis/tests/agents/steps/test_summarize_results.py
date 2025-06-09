# aegis/tests/agents/steps/test_summarize_result.py
"""
Unit tests for the summarize_result agent step.
"""
import pytest

from aegis.agents.plan_output import AgentScratchpad
from aegis.agents.steps.summarize_result import summarize_result
from aegis.agents.task_state import TaskState
from aegis.schemas.runtime import RuntimeExecutionConfig


@pytest.fixture
def populated_state() -> TaskState:
    """Provides a TaskState with a history of two steps."""
    runtime = RuntimeExecutionConfig()
    state = TaskState(
        task_id="summary-test-123", task_prompt="Test summarization", runtime=runtime
    )

    plan1 = AgentScratchpad(
        thought="First step.", tool_name="tool_one", tool_args={"arg": "A"}
    )
    result1 = "Output of tool one."

    plan2 = AgentScratchpad(
        thought="Second step.", tool_name="tool_two", tool_args={"arg": "B"}
    )
    result2 = "Output of tool two."

    state.history = [(plan1, result1), (plan2, result2)]
    return state


def test_summarize_with_history(populated_state: TaskState):
    """Verify that a summary is correctly generated from a populated history."""
    result_dict = summarize_result(populated_state)
    summary = result_dict.get("final_summary")

    assert summary is not None
    # Check for key components from the state
    assert "AEGIS Task Report: summary-test-123" in summary
    assert "Goal:** Test summarization" in summary
    # Check for components from step 1
    assert "Step 1: tool_one" in summary
    assert "Thought:** First step." in summary
    assert "Output of tool one." in summary
    # Check for components from step 2
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
