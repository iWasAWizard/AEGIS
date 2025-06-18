# aegis/tests/agents/test_task_state.py
"""
Unit tests for the TaskState data model.
"""
from aegis.agents.task_state import TaskState, HistoryEntry
from aegis.schemas.plan_output import AgentScratchpad
from aegis.schemas.runtime import RuntimeExecutionConfig


def test_task_state_initialization():
    """Verify that a new TaskState object initializes with correct defaults."""
    state = TaskState(
        task_id="init-test",
        task_prompt="A test prompt",
        runtime=RuntimeExecutionConfig()
    )

    assert state.task_id == "init-test"
    assert state.task_prompt == "A test prompt"
    assert state.latest_plan is None
    assert state.history == []
    assert state.final_summary is None
    assert state.steps_taken == 0


def test_steps_taken_property():
    """Verify the steps_taken property correctly reflects the history length."""
    state = TaskState(
        task_id="steps-test",
        task_prompt="A test prompt",
        runtime=RuntimeExecutionConfig()
    )

    assert state.steps_taken == 0

    # Add one entry
    plan1 = AgentScratchpad(thought="t1", tool_name="tool1", tool_args={})
    entry1 = HistoryEntry(plan=plan1, observation="o1", status="success")
    state.history.append(entry1)

    assert state.steps_taken == 1

    # Add a second entry
    plan2 = AgentScratchpad(thought="t2", tool_name="tool2", tool_args={})
    entry2 = HistoryEntry(plan=plan2, observation="o2", status="success")
    state.history.append(entry2)

    assert state.steps_taken == 2
