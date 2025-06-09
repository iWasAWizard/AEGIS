# aegis/tests/tools/test_tool_execution.py
"""
Tests for individual tool execution logic and the execute_tool step.
"""
import asyncio
import subprocess
from unittest.mock import MagicMock

import pytest

from aegis.agents.steps.execute_tool import execute_tool
from aegis.agents.task_state import TaskState
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.tools.primitives.primitive_system import (
    RunLocalCommandInput,
    run_local_command,
)
from schemas.plan_output import AgentScratchpad


def test_run_local_command_success(monkeypatch):
    """Verify that run_local_command executes and returns stdout."""
    mock_result = MagicMock()
    mock_result.stdout = "hello world"
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_run = MagicMock(return_value=mock_result)
    monkeypatch.setattr(subprocess, "run", mock_run)

    input_data = RunLocalCommandInput(command="echo 'hello world'")
    result = run_local_command(input_data)

    mock_run.assert_called_once()
    assert result == "hello world"


def test_run_local_command_with_stderr(monkeypatch):
    """Verify that run_local_command includes stderr in its output."""
    mock_result = MagicMock()
    mock_result.stdout = "some output"
    mock_result.stderr = "this is an error"
    mock_result.returncode = 1
    mock_run = MagicMock(return_value=mock_result)
    monkeypatch.setattr(subprocess, "run", mock_run)

    input_data = RunLocalCommandInput(command="command_that_fails")
    result = run_local_command(input_data)

    assert "some output" in result
    assert "[STDERR]" in result
    assert "this is an error" in result


def test_run_local_command_exception(monkeypatch):
    """Verify that the tool handles exceptions during subprocess execution."""
    mock_run = MagicMock(
        side_effect=subprocess.TimeoutExpired(cmd="timeout_cmd", timeout=10)
    )
    monkeypatch.setattr(subprocess, "run", mock_run)

    input_data = RunLocalCommandInput(command="timeout_cmd")
    result = run_local_command(input_data)

    assert "[ERROR]" in result
    assert "Command execution failed" in result


@pytest.mark.asyncio
async def test_execute_tool_with_invalid_args():
    """
    Verify that execute_tool handles Pydantic validation errors when the LLM
    provides incorrect arguments for a tool.
    """
    invalid_plan = AgentScratchpad(
        thought="I am providing the wrong arguments.",
        tool_name="run_local_command",
        tool_args={"cmd": "echo 'this will fail'"},
    )

    state = TaskState(
        task_id="test-invalid-args",
        task_prompt="test",
        runtime=RuntimeExecutionConfig(),
        latest_plan=invalid_plan,
    )

    result_dict = await execute_tool(state)

    _plan, output = result_dict["history"][0]
    assert "[ERROR]" in output
    assert "failed during execution" in output
    assert "extra fields not permitted" in output


@pytest.mark.asyncio
async def test_execute_tool_timeout(monkeypatch):
    """Verify that the execute_tool step correctly handles a tool timeout."""

    # This mock tool will "run" for longer than the timeout.
    async def slow_tool(_):
        await asyncio.sleep(0.2)
        return "This should not be returned."

    # Mock get_tool to return our slow tool
    mock_tool_entry = MagicMock()
    mock_tool_entry.run = slow_tool
    mock_tool_entry.input_model = lambda **kwargs: {}  # A dummy model instance
    monkeypatch.setattr(
        "aegis.agents.steps.execute_tool.get_tool",
        MagicMock(return_value=mock_tool_entry),
    )

    plan = AgentScratchpad(thought="test timeout", tool_name="slow_tool", tool_args={})
    state = TaskState(
        task_id="test-timeout",
        task_prompt="test",
        # Set a very short timeout
        runtime=RuntimeExecutionConfig(timeout=1),
        latest_plan=plan,
    )

    # Override the sleep time to be less than the timeout
    # This is a bit of a trick to test the timeout logic without waiting.
    # We set the tool to sleep for 0.2s, and timeout to 0.1s.
    state.runtime.timeout = 0.1

    result_dict = await execute_tool(state)

    _plan, output = result_dict["history"][0]
    assert "[ERROR]" in output
    assert "failed during execution" in output
