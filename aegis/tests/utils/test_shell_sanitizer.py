from aegis.utils.shell_sanitizer import is_shell_safe


def test_shell_sanitizer_blocks_dangerous():
    result = is_shell_safe("rm -rf /")
    assert result["valid"] is False
    assert "Unsafe token" in result["reason"]


def test_shell_sanitizer_allows_safe():
    result = is_shell_safe("echo hello")
    assert result["valid"] is True
