# tests/agents/test_reflect_and_plan.py

import pytest
import yaml

from aegis.agents.steps.reflect_and_plan import reflect_and_plan
from aegis.agents.task_state import TaskState


@pytest.mark.asyncio
async def test_reflect_success():
    async def mock_llm_chat(_: str) -> str:
        return yaml.dump(["whoami", "nmap -p 1-65535 localhost"])

    # noinspection PyArgumentList
    state = TaskState(
        task_id="xyz", task_prompt="Find open ports", llm_query=mock_llm_chat
    )

    updated = await reflect_and_plan(state)

    assert updated.plan == ["whoami", "nmap -p 1-65535 localhost"]
    assert updated.steps_taken == 1
    assert updated.analysis[-1].startswith("Reflection")


@pytest.mark.asyncio
async def test_reflect_invalid_yaml():
    async def mock_llm_chat(_: str) -> str:
        return "this: is: not: yaml"

    # noinspection PyArgumentList
    state = TaskState(
        task_id="bad_yaml", task_prompt="Break it", llm_query=mock_llm_chat
    )

    updated = await reflect_and_plan(state)

    assert updated.plan == []
    assert updated.steps_taken == 1
    assert "Reflection" in updated.analysis[-1]
