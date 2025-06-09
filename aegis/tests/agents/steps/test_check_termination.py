# aegis/tests/agents/steps/test_check_termination.py
"""
Unit tests for the check_termination agent step.
"""
import pytest
from aegis.agents.plan_output import AgentScratchpad
from aegis.agents.steps.check_termination import check_termination
from aegis.agents.task_state import TaskState
from aegis.schemas.runtime import RuntimeExecutionConfig


@pytest.fixture
def base_state() -> TaskState:
    """Provides a basic, non-terminating TaskState."""
    return TaskState(
        task_id="test-term",
        task_prompt="test prompt",
        runtime=RuntimeExecutionConfig(iterations=10),
    )


def test_continue_on_empty_history(base_state: TaskState):
    """The agent should continue if no steps have been taken yet."""
    assert check_termination(base_state) == "continue"


def test_continue_on_normal_step(base_state: TaskState):
    """The agent should continue after a normal tool execution."""
    plan = AgentScratchpad(thought="test", tool_name="some_tool", tool_args={})
    base_state.history = [(plan, "some result")]
    assert check_termination(base_state) == "continue"


def test_terminate_on_finish_tool(base_state: TaskState):
    """The agent must terminate if the last tool used was 'finish'."""
    plan = AgentScratchpad(thought="finish", tool_name="finish", tool_args={})
    base_state.history = [(plan, "Task finished by agent.")]
    assert check_termination(base_state) == "end"


def test_terminate_on_max_iterations(base_state: TaskState):
    """The agent must terminate if it has reached its iteration limit."""
    # Set history to have the same number of steps as the iteration limit
    base_state.runtime.iterations = 3
    plan = AgentScratchpad(thought="test", tool_name="some_tool", tool_args={})
    base_state.history = [(plan, "")] * 3

    assert base_state.steps_taken == 3
    assert check_termination(base_state) == "end"


def test_no_terminate_before_max_iterations(base_state: TaskState):
    """The agent should not terminate if it is below its iteration limit."""
    base_state.runtime.iterations = 5
    plan = AgentScratchpad(thought="test", tool_name="some_tool", tool_args={})
    base_state.history = [(plan, "")] * 4

    assert base_state.steps_taken < 5
    assert check_termination(base_state) == "continue"
