# aegis/tests/tools/wrappers/test_pwn_wrapper.py
"""
Unit tests for the pwntools wrapper tools.
"""
from unittest.mock import MagicMock, patch

import pytest

from aegis.exceptions import ToolExecutionError
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

# Import pwntools for the non-executor tools if available
try:
    from pwn import (
        context as pwn_context,
        shellcraft as pwn_shellcraft,
        ELF as pwn_ELF,
        cyclic as pwn_cyclic,
        cyclic_find as pwn_cyclic_find,
    )  # type: ignore

    PWNTOOLS_AVAILABLE_FOR_NON_EXECUTOR_TOOLS = True
except ImportError:
    PWNTOOLS_AVAILABLE_FOR_NON_EXECUTOR_TOOLS = False


# --- Fixtures for Executor-based tools ---


@pytest.fixture
def mock_pwntools_executor_interact_remote(monkeypatch):
    """Mocks PwntoolsExecutor.interact_remote method."""
    mock_method = MagicMock(return_value="mocked remote interaction output")
    monkeypatch.setattr(
        "aegis.executors.pwntools.PwntoolsExecutor.interact_remote", mock_method
    )
    return mock_method


@pytest.fixture
def mock_pwntools_executor_interact_process(monkeypatch):
    """Mocks PwntoolsExecutor.interact_process method."""
    mock_method = MagicMock(return_value="mocked process interaction output")
    monkeypatch.setattr(
        "aegis.executors.pwntools.PwntoolsExecutor.interact_process", mock_method
    )
    return mock_method


@pytest.fixture
def mock_pwntools_executor_init(monkeypatch):
    """Mocks PwntoolsExecutor.__init__ to check instantiation."""
    mock_init = MagicMock(return_value=None)
    monkeypatch.setattr("aegis.executors.pwntools.PwntoolsExecutor.__init__", mock_init)
    return mock_init


# --- Fixtures for Non-Executor tools (mocking pwn library directly) ---
# These remain largely the same as before, ensuring PWNTOOLS_AVAILABLE check.


@pytest.fixture
def mock_pwn_context(monkeypatch):
    if not PWNTOOLS_AVAILABLE_FOR_NON_EXECUTOR_TOOLS:
        pytest.skip("pwntools not available for non-executor tests")
    mock_context = MagicMock()
    monkeypatch.setattr("aegis.tools.wrappers.pwn.context", mock_context)
    return mock_context


@pytest.fixture
def mock_pwn_shellcraft(monkeypatch):
    if not PWNTOOLS_AVAILABLE_FOR_NON_EXECUTOR_TOOLS:
        pytest.skip("pwntools not available for non-executor tests")
    mock = MagicMock()
    mock.sh.return_value = "asm_for_sh"
    monkeypatch.setattr("aegis.tools.wrappers.pwn.shellcraft", mock)
    return mock


@pytest.fixture
def mock_pwn_elf(monkeypatch):
    if not PWNTOOLS_AVAILABLE_FOR_NON_EXECUTOR_TOOLS:
        pytest.skip("pwntools not available for non-executor tests")
    mock = MagicMock()
    mock_elf_instance = MagicMock()
    mock_elf_instance.path = "/bin/ls"
    mock_elf_instance.arch = "amd64"
    mock_elf_instance.bits = 64
    mock_elf_instance.os = "linux"
    mock_elf_instance.relro = "Full"
    mock_elf_instance.pie = True
    mock_elf_instance.nx = True
    mock_elf_instance.canary = True
    mock_elf_instance.functions = {"main": MagicMock(), "printf": MagicMock()}
    mock.return_value = mock_elf_instance
    monkeypatch.setattr("aegis.tools.wrappers.pwn.ELF", mock)
    return mock


# --- Tests for Executor-based Tools ---


def test_pwn_remote_connect_success(
    mock_pwntools_executor_init, mock_pwntools_executor_interact_remote
):
    """Verify pwn_remote_connect calls executor and returns its result."""
    input_data = PwnRemoteConnectInput(
        host="localhost", port=1234, payload="hello", timeout=10
    )
    result = pwn_remote_connect(input_data)

    mock_pwntools_executor_init.assert_called_once_with(default_timeout=10)
    mock_pwntools_executor_interact_remote.assert_called_once()

    # Check arguments passed to interact_remote
    args, kwargs = mock_pwntools_executor_interact_remote.call_args
    assert args[0] == "localhost"  # host
    assert args[1] == 1234  # port
    assert callable(args[2])  # interaction_func
    assert kwargs["timeout"] == 10

    assert result == "mocked remote interaction output"


def test_pwn_remote_connect_failure_propagates(
    mock_pwntools_executor_init, mock_pwntools_executor_interact_remote
):
    """Verify ToolExecutionError from executor propagates."""
    mock_pwntools_executor_interact_remote.side_effect = ToolExecutionError(
        "PwntoolsExecutor remote failed"
    )
    input_data = PwnRemoteConnectInput(host="localhost", port=1234)

    with pytest.raises(ToolExecutionError, match="PwntoolsExecutor remote failed"):
        pwn_remote_connect(input_data)
    mock_pwntools_executor_init.assert_called_once()
    mock_pwntools_executor_interact_remote.assert_called_once()


def test_pwn_process_interaction_success(
    mock_pwntools_executor_init, mock_pwntools_executor_interact_process
):
    """Verify pwn_process_interaction calls executor and returns its result."""
    input_data = PwnProcessInteractionInput(
        file_path="/bin/test", payload="input", timeout=7
    )
    result = pwn_process_interaction(input_data)

    mock_pwntools_executor_init.assert_called_once_with(default_timeout=7)
    mock_pwntools_executor_interact_process.assert_called_once()

    args, kwargs = mock_pwntools_executor_interact_process.call_args
    assert args[0] == "/bin/test"  # executable_path
    assert callable(args[1])  # interaction_func
    assert kwargs["timeout"] == 7

    assert result == "mocked process interaction output"


def test_pwn_process_interaction_failure_propagates(
    mock_pwntools_executor_init, mock_pwntools_executor_interact_process
):
    """Verify ToolExecutionError from executor propagates."""
    mock_pwntools_executor_interact_process.side_effect = ToolExecutionError(
        "PwntoolsExecutor process failed"
    )
    input_data = PwnProcessInteractionInput(file_path="/bin/test", payload="input")

    with pytest.raises(ToolExecutionError, match="PwntoolsExecutor process failed"):
        pwn_process_interaction(input_data)
    mock_pwntools_executor_init.assert_called_once()
    mock_pwntools_executor_interact_process.assert_called_once()


# --- Tests for Non-Executor Tools (remain mostly the same, ensure PWNTOOLS_AVAILABLE check) ---


def test_pwn_shellcode_craft(mock_pwn_context, mock_pwn_shellcraft):
    """Verify the tool sets the correct context and calls shellcraft."""
    if not PWNTOOLS_AVAILABLE_FOR_NON_EXECUTOR_TOOLS:
        pytest.skip("pwntools not available")
    input_data = PwnShellcodeCraftInput(arch="i386", os="linux", command="sh")
    result = pwn_shellcode_craft(input_data)

    assert mock_pwn_context.arch == "i386"
    assert mock_pwn_context.os == "linux"
    mock_pwn_shellcraft.sh.assert_called_once()
    assert result == "asm_for_sh"


@patch("aegis.tools.wrappers.pwn.cyclic", new_callable=MagicMock)
@patch("aegis.tools.wrappers.pwn.cyclic_find", new_callable=MagicMock)
def test_pwn_cyclic_pattern(mock_cyclic_find_func, mock_cyclic_func):
    """Verify the tool calls the correct cyclic function based on input."""
    if not PWNTOOLS_AVAILABLE_FOR_NON_EXECUTOR_TOOLS:
        pytest.skip("pwntools not available")

    # Test generation
    mock_cyclic_func.return_value = b"aaabaaacaaadaaae"
    input_gen = PwnCyclicPatternInput(length=16)
    result_gen = pwn_cyclic_pattern(input_gen)
    mock_cyclic_func.assert_called_once_with(16, n=4)
    assert "aaabaaacaaadaaae" in result_gen

    # Test finding
    mock_cyclic_find_func.return_value = 4
    input_find = PwnCyclicPatternInput(length=100, find="baaa")  # find value is str
    result_find = pwn_cyclic_pattern(input_find)
    mock_cyclic_find_func.assert_called_once_with(
        b"baaa", n=4
    )  # pwntools expects bytes
    assert "Offset for 'baaa' is: 4" in result_find


def test_pwn_elf_inspector(mock_pwn_elf):
    """Verify the tool inspects an ELF and formats the properties correctly."""
    if not PWNTOOLS_AVAILABLE_FOR_NON_EXECUTOR_TOOLS:
        pytest.skip("pwntools not available")
    input_data = PwnElfInspectorInput(file_path="/bin/ls")
    result = pwn_elf_inspector(input_data)

    # Check that the mock_pwn_elf (which is pwn.ELF) was called
    # The return value of this fixture is the *class*, not the instance.
    # We need to check that aegis.tools.wrappers.pwn.ELF was called.
    # This is implicitly tested by the fact that we get results from the mocked instance.
    # A more direct way if pwn_ELF was the class: pwn_ELF.assert_called_once_with("/bin/ls")

    assert "Arch: amd64" in result
    assert "RELRO: Full" in result
    assert "PIE: True" in result
    assert "Canary: True" in result
    # Accessing keys of a MagicMock directly might not work as expected for elf.functions.keys()
    # The original test was okay because mock_elf_instance.functions was a dict.
    # If mock_pwn_elf itself is the ELF class, then the instance is created inside the tool.
    # The check below assumes the mock setup correctly returns a dictionary-like object for functions.
    assert "Functions (first 10): ['main', 'printf']" in result


def test_tool_raises_if_pwntools_not_available(monkeypatch):
    """Verify tools raise ToolExecutionError if pwntools is not installed."""
    monkeypatch.setattr("aegis.tools.wrappers.pwn.PWNTOOLS_AVAILABLE", False)
    monkeypatch.setattr(
        "aegis.executors.pwntools.PWNTOOLS_AVAILABLE_FOR_EXECUTOR", False
    )

    with pytest.raises(
        ToolExecutionError, match="The 'pwntools' library is not installed"
    ):
        pwn_remote_connect(PwnRemoteConnectInput(host="h", port=1))
    with pytest.raises(
        ToolExecutionError, match="The 'pwntools' library is not installed"
    ):
        pwn_process_interaction(PwnProcessInteractionInput(file_path="f", payload="p"))
    with pytest.raises(
        ToolExecutionError, match="The 'pwntools' library is not installed"
    ):
        pwn_shellcode_craft(PwnShellcodeCraftInput())
    with pytest.raises(
        ToolExecutionError, match="The 'pwntools' library is not installed"
    ):
        pwn_cyclic_pattern(PwnCyclicPatternInput())
    with pytest.raises(
        ToolExecutionError, match="The 'pwntools' library is not installed"
    ):
        pwn_elf_inspector(PwnElfInspectorInput(file_path="f"))
