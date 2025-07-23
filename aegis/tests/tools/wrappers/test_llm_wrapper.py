# aegis/tests/tools/wrappers/test_llm_wrapper.py
"""
Unit tests for the LLM wrapper tool.
"""
from unittest.mock import AsyncMock

import pytest

from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolExecutionError
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.tools.wrappers.llm import invoke_llm, InvokeLlmInput


@pytest.mark.asyncio
async def test_invoke_llm_success():
    """Verify the tool calls the provider's get_completion method and returns its result."""
    mock_provider = AsyncMock()
    mock_provider.get_completion.return_value = "LLM response"

    state = TaskState(
        task_id="t1", task_prompt="p", runtime=RuntimeExecutionConfig()
    )
    input_data = InvokeLlmInput(
        system_prompt="You are a helpful assistant.", user_prompt="What is AI?"
    )

    result = await invoke_llm(input_data, state, mock_provider)

    mock_provider.get_completion.assert_awaited_once()
    call_args, _ = mock_provider.get_completion.call_args
    assert call_args[0] == [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is AI?"},
    ]
    assert call_args[1] == state.runtime
    assert result == "LLM response"


@pytest.mark.asyncio
async def test_invoke_llm_provider_fails():
    """Verify that an exception from the provider is raised as a ToolExecutionError."""
    mock_provider = AsyncMock()
    mock_provider.get_completion.side_effect = Exception("Backend connection failed")

    state = TaskState(
        task_id="t1", task_prompt="p", runtime=RuntimeExecutionConfig()
    )
    input_data = InvokeLlmInput(system_prompt="sys", user_prompt="usr")

    with pytest.raises(ToolExecutionError, match="Direct LLM invocation failed"):
        await invoke_llm(input_data, state, mock_provider)