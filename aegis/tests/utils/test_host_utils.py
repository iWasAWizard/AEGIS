# aegis/tests/utils/test_host_utils.py
"""
Unit tests for the host utility functions.
"""
import pytest

from aegis.utils.host_utils import get_user_host_from_string


def test_get_user_host_from_string_success():
    """Verify that a correctly formatted 'user@host' string is parsed."""
    host_str = "testuser@example.com"
    user, host = get_user_host_from_string(host_str)

    assert user == "testuser"
    assert host == "example.com"


def test_get_user_host_from_string_malformed():
    """Verify that a string without an '@' raises a ValueError."""
    host_str = "justahostname"
    with pytest.raises(ValueError, match="must be in 'user@host' format"):
        get_user_host_from_string(host_str)
