from aegis.agents.steps.route_execution import route_execution
from aegis.agents.task_state import TaskState

import pytest


# noinspection PyArgumentList
@pytest.mark.asyncio
async def test_route_exec_basic():
    state = TaskState(
        task_id="test123",
        task_prompt="echo hello",
        plan=["echo hello", "echo goodbye"],
        results=[],
    )
    updated = await route_execution(state)
    assert len(updated.results) == 2
    assert "echo hello" in updated.results[0]


# noinspection PyArgumentList
@pytest.mark.asyncio
async def test_route_exec_empty_plan():
    state = TaskState(task_id="empty456", task_prompt="noop", plan=[], results=[])
    updated = await route_execution(state)
    assert updated.results == []
