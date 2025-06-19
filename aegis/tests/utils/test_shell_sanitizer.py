# aegis/tests/utils/test_shell_sanitizer.py
"""
Unit tests for the prompt and shell safety utilities.
"""
import pytest

from aegis.utils.shell_sanitizer import (
    is_prompt_safe,
    validate_shell_command,
    sanitize_shell_arg,
)


# --- Prompt Safety Tests ---


@pytest.mark.parametrize(
    "unsafe_phrase",
    [
        "ignore previous instructions",
        "rm -rf /",
        "run a fork bomb",
        "format my disk",
    ],
)
def test_is_prompt_safe_detects_unsafe_phrases(unsafe_phrase):
    """Verify that prompts containing blacklisted phrases are detected as unsafe."""
    assert is_prompt_safe(f"My prompt is to {unsafe_phrase}") is False


def test_is_prompt_safe_allows_benign_prompt():
    """Verify that a normal, safe prompt is allowed."""
    assert is_prompt_safe("Please list the files in the current directory.") is True


# --- Shell Safety Tests ---


@pytest.mark.parametrize(
    "unsafe_command",
    [
        "ls; whoami",
        "cat /etc/passwd | grep root",
        "command1 && command2",
        "command1 || command2",
        "echo `reboot`",
        "echo $(reboot)",
        "cat > /etc/shadows",
        "command < /etc/hosts",
    ],
)
def test_validate_shell_command_detects_unsafe_patterns(unsafe_command):
    """Verify that commands with forbidden shell metacharacters are detected as unsafe."""
    is_safe, reason = validate_shell_command(unsafe_command)
    assert is_safe is False
    assert "Unsafe pattern detected" in reason


def test_validate_shell_command_allows_safe_command():
    """Verify that a simple command with arguments is considered safe."""
    is_safe, reason = validate_shell_command("ls -la /tmp/my_folder")
    assert is_safe is True
    assert reason == "Command is safe."


def test_sanitize_shell_arg():
    """Verify that shell arguments are correctly quoted."""
    # An argument that could be dangerous if not quoted
    unsafe_arg = "my file; ls"

    # After sanitization, it should be treated as a single, literal string
    sanitized_arg = sanitize_shell_arg(unsafe_arg)

    # shlex.quote will wrap it in single quotes
    assert sanitized_arg == "'my file; ls'"
