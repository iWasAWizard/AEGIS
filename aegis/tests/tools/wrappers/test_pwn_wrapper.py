# aegis/tests/tools/wrappers/test_pwn_wrapper.py
"""
Unit tests for the pwntools wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.executors.pwntools_exec import PwntoolsExecutor
from aegis.tools.wrappers.pwn import (
    pwn_remote_connect,
    PwnRemoteConnectInput,
    pwn_shellcode_craft,
    PwnShellcodeCraftInput,
    pwn_cyclic_pattern,
    PwnCyclicPatternInput,
    pwn_elf_inspector,
    PwnElfInspectorInput,
    pwn_process_interaction,
    PwnProcessInteractionInput,
)

pytest.importorskip("pwn", reason="pwntools not installed, skipping pwn wrapper tests")


# --- Fixtures for Executor-based tools ---


@pytest.fixture
def mock_pwntools_executor(monkeypatch):
    """Mocks all methods of the PwntoolsExecutor class."""
    mock = MagicMock()
    mock.interact_remote.return_value = "mocked remote interaction"
    mock.interact_process.return_value = "mocked process interaction"
    mock.craft_shellcode.return_value = "mocked shellcode asm"
    mock.generate_cyclic_pattern.return_value = "mocked cyclic pattern"
    mock.inspect_elf.return_value = "mocked elf inspection"

    # Patch the class in the module where it's used
    monkeypatch.setattr(
        "aegis.tools.wrappers.pwn.PwntoolsExecutor", lambda *args, **kwargs: mock
    )
    return mock


# --- Tests ---


def test_pwn_remote_connect_success(mock_pwntools_executor):
    """Verify pwn_remote_connect calls executor and returns its result."""
    input_data = PwnRemoteConnectInput(
        host="localhost", port=1234, payload="hello", timeout=10
    )
    result = pwn_remote_connect(input_data)

    mock_pwntools_executor.interact_remote.assert_called_once()
    assert result == "mocked remote interaction"


def test_pwn_process_interaction_success(mock_pwntools_executor):
    """Verify pwn_process_interaction calls executor and returns its result."""
    input_data = PwnProcessInteractionInput(
        file_path="/bin/test", payload="input", timeout=10
    )
    result = pwn_process_interaction(input_data)

    mock_pwntools_executor.interact_process.assert_called_once()
    assert result == "mocked process interaction"


def test_pwn_shellcode_craft_success(mock_pwntools_executor):
    """Verify pwn_shellcode_craft calls the executor."""
    input_data = PwnShellcodeCraftInput(arch="amd64", os="linux", command="sh")
    result = pwn_shellcode_craft(input_data)

    mock_pwntools_executor.craft_shellcode.assert_called_once_with(
        "amd64", "linux", "sh"
    )
    assert result == "mocked shellcode asm"


def test_pwn_cyclic_pattern_success(mock_pwntools_executor):
    """Verify pwn_cyclic_pattern calls the executor."""
    input_data = PwnCyclicPatternInput(length=200, find=None)
    result = pwn_cyclic_pattern(input_data)

    mock_pwntools_executor.generate_cyclic_pattern.assert_called_once_with(200, None)
    assert result == "mocked cyclic pattern"


def test_pwn_elf_inspector_success(mock_pwntools_executor):
    """Verify pwn_elf_inspector calls the executor."""
    input_data = PwnElfInspectorInput(file_path="/bin/ls")
    result = pwn_elf_inspector(input_data)

    mock_pwntools_executor.inspect_elf.assert_called_once_with("/bin/ls")
    assert result == "mocked elf inspection"


def test_pwn_tool_failure_propagation(mock_pwntools_executor):
    """Verify that a ToolExecutionError from the executor propagates up."""
    mock_pwntools_executor.interact_remote.side_effect = ToolExecutionError(
        "Executor failed"
    )

    input_data = PwnRemoteConnectInput(
        host="host", port=123, payload="test", timeout=10
    )
    with pytest.raises(ToolExecutionError, match="Executor failed"):
        pwn_remote_connect(input_data)


def test_pwn_tool_raises_if_pwntools_not_available(monkeypatch):
    """Verify tools raise ToolExecutionError if pwntools is not installed."""
    monkeypatch.setattr(
        "aegis.tools.wrappers.pwn.PWNTOOLS_AVAILABLE_FOR_EXECUTOR", False
    )

    with pytest.raises(
        ToolExecutionError, match="The 'pwntools' library is not installed."
    ):
        pwn_remote_connect(
            PwnRemoteConnectInput(host="h", port=1, payload="test", timeout=10)
        )
