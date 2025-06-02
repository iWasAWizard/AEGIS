import pytest
from aegis.agents.steps.check_termination import check_termination
from aegis.agents.task_state import TaskState


@pytest.mark.asyncio
async def test_termination_by_done():
    # noinspection PyArgumentList
    state = TaskState(task_id="t", task_prompt="x", done=True, terminate_reason="test")
    result = await check_termination(state)
    assert result == "end"


@pytest.mark.asyncio
async def test_termination_by_steps():
    state = TaskState(task_id="t", task_prompt="x", steps_taken=25)
    result = await check_termination(state)
    assert result == "end"


@pytest.mark.asyncio
async def test_termination_by_signal():
    # noinspection PyArgumentList
    state = TaskState(
        task_id="t",
        task_prompt="x",
        selected_tool="finish",
        tool_args={"reason": "wrap it"},
    )
    result = await check_termination(state)
    assert result == "end"


@pytest.mark.asyncio
async def test_continue_loop():
    # noinspection PyArgumentList
    state = TaskState(task_id="t", task_prompt="x", steps_taken=1, selected_tool="doit")
    result = await check_termination(state)
    assert result == "continue"
