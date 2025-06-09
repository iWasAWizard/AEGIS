# aegis/tests/tools/primitives/test_filesystem_primitive.py
"""
Unit tests for the filesystem primitive tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.primitives.primitive_filesystem import (
    create_random_file, CreateRandomFileInput,
    diff_text_blocks, DiffTextBlocksInput
)


# --- Fixtures ---

@pytest.fixture
def mock_run_local_command(monkeypatch):
    """Mocks the underlying run_local_command primitive."""
    mock = MagicMock(return_value="dd command output")
    monkeypatch.setattr("aegis.tools.primitives.primitive_filesystem.run_local_command", mock)
    return mock


# --- Tests ---

@pytest.mark.parametrize(
    "size_input, expected_dd_command",
    [
        ("10k", "dd if=/dev/urandom of='test.dat' bs=1K count=10"),
        ("25M", "dd if=/dev/urandom of='test.dat' bs=1K count=25600"),
        ("1G", "dd if=/dev/urandom of='test.dat' bs=1K count=1048576"),
        ("512", "dd if=/dev/urandom of='test.dat' bs=1K count=1"),
        ("1024", "dd if=/dev/urandom of='test.dat' bs=1K count=1"),
        ("0", "dd if=/dev/urandom of='test.dat' bs=1K count=0"),
    ]
)
def test_create_random_file_command_generation(mock_run_local_command, size_input, expected_dd_command):
    """Verify that create_random_file constructs the correct dd command for various size inputs."""
    input_data = CreateRandomFileInput(file_path="test.dat", size=size_input)
    create_random_file(input_data)

    # Check that the mock was called
    mock_run_local_command.assert_called_once()

    # Get the RunLocalCommandInput object passed to the mock
    call_args = mock_run_local_command.call_args[0][0]

    # Assert the generated command string is correct
    assert call_args.command == expected_dd_command


def test_create_random_file_invalid_size():
    """Verify the tool returns an error for an invalid size format."""
    input_data = CreateRandomFileInput(file_path="test.dat", size="10megabytes")
    result = create_random_file(input_data)
    assert "[ERROR] Invalid size format" in result


def test_diff_text_blocks():
    """Verify that diff_text_blocks produces a correct unified diff."""
    old_text = "hello world\nthis is line 2\ngoodbye"
    new_text = "hello mars\nthis is line 2\nfarewell"

    input_data = DiffTextBlocksInput(old=old_text, new=new_text)
    result = diff_text_blocks(input_data)

    # Check for essential components of a unified diff
    assert "--- old" in result
    assert "+++ new" in result
    assert "@@ -1,3 +1,3 @@" in result
    assert "-hello world" in result
    assert "+hello mars" in result
    assert " this is line 2" in result
    assert "-goodbye" in result
    assert "+farewell" in result
