# aegis/tests/tools/wrappers/test_pwn_wrapper.py
"""
Unit tests for the pwntools wrapper tools.
"""
from unittest.mock import MagicMock, patch

import pytest

# Mark this entire module to be skipped if pwntools is not installed
pwn = pytest.importorskip("pwn", reason="pwntools not installed, skipping pwn tests")

from aegis.tools.wrappers.pwn import (
    pwn_remote_connect, PwnRemoteConnectInput,
    pwn_shellcode_craft, PwnShellcodeCraftInput,
    pwn_cyclic_pattern, PwnCyclicPatternInput,
    pwn_elf_inspector, PwnElfInspectorInput,
    pwn_process_interaction, PwnProcessInteractionInput,
)


# --- Fixtures ---

@pytest.fixture
def mock_pwn_remote(monkeypatch):
    mock = MagicMock()
    mock_conn = MagicMock()
    mock_conn.recvall.return_value = b"server response"
    mock.return_value = mock_conn
    monkeypatch.setattr(pwn, "remote", mock)
    return mock


@pytest.fixture
def mock_pwn_context(monkeypatch):
    # This is a bit tricky as context is a special object
    mock_context = MagicMock()
    monkeypatch.setattr(pwn, "context", mock_context)
    return mock_context


@pytest.fixture
def mock_pwn_shellcraft(monkeypatch):
    mock = MagicMock()
    mock.sh.return_value = "asm_for_sh"
    monkeypatch.setattr(pwn, "shellcraft", mock)
    return mock


@pytest.fixture
def mock_pwn_elf(monkeypatch):
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
    monkeypatch.setattr(pwn, "ELF", mock)
    return mock


# --- Tests ---

def test_pwn_remote_connect(mock_pwn_remote):
    """Verify the tool calls pwn.remote and handles the connection correctly."""
    input_data = PwnRemoteConnectInput(host="localhost", port=1234, payload="hello")
    result = pwn_remote_connect(input_data)

    mock_pwn_remote.assert_called_once_with("localhost", 1234, timeout=5)
    conn = mock_pwn_remote.return_value
    conn.sendline.assert_called_once_with(b"hello")
    assert result == "server response"


def test_pwn_shellcode_craft(mock_pwn_context, mock_pwn_shellcraft):
    """Verify the tool sets the correct context and calls shellcraft."""
    input_data = PwnShellcodeCraftInput(arch="i386", os="linux", command="sh")
    result = pwn_shellcode_craft(input_data)

    assert mock_pwn_context.arch == "i386"
    assert mock_pwn_context.os == "linux"
    mock_pwn_shellcraft.sh.assert_called_once()
    assert result == "asm_for_sh"


@patch("pwn.cyclic")
@patch("pwn.cyclic_find")
def test_pwn_cyclic_pattern(mock_cyclic_find, mock_cyclic):
    """Verify the tool calls the correct cyclic function based on input."""
    # Test generation
    mock_cyclic.return_value = b"aaabaaacaaadaaae"
    input_gen = PwnCyclicPatternInput(length=16)
    result_gen = pwn_cyclic_pattern(input_gen)
    mock_cyclic.assert_called_once_with(16, n=4)
    assert "aaabaaacaaadaaae" in result_gen

    # Test finding
    mock_cyclic_find.return_value = 4
    input_find = PwnCyclicPatternInput(length=100, find="baaa")
    result_find = pwn_cyclic_pattern(input_find)
    mock_cyclic_find.assert_called_once_with(b"baaa", n=4)
    assert "Offset for 'baaa' is: 4" in result_find


def test_pwn_elf_inspector(mock_pwn_elf):
    """Verify the tool inspects an ELF and formats the properties correctly."""
    input_data = PwnElfInspectorInput(file_path="/bin/ls")
    result = pwn_elf_inspector(input_data)

    mock_pwn_elf.assert_called_once_with("/bin/ls")
    assert "Arch: amd64" in result
    assert "RELRO: Full" in result
    assert "PIE: True" in result
    assert "Canary: True" in result
    assert "Functions: ['main', 'printf']" in result


@patch("pwn.process")
def test_pwn_process_interaction(mock_pwn_process):
    """Verify the tool starts a local process and interacts with it."""
    mock_proc_instance = MagicMock()
    mock_proc_instance.recvall.return_value = b"process output"
    mock_pwn_process.return_value = mock_proc_instance

    input_data = PwnProcessInteractionInput(file_path="/bin/test", payload="input")
    result = pwn_process_interaction(input_data)

    mock_pwn_process.assert_called_once_with("/bin/test")
    mock_proc_instance.sendline.assert_called_once_with(b"input")
    assert result == "process output"
