# aegis/tests/tools/wrappers/test_local_filesystem_wrapper.py
"""
Unit tests for the consolidated local filesystem wrapper tools.
"""
from pathlib import Path

import pytest

from aegis.tools.wrappers.wrapper_local_filesystem import (
    diff_local_file_after_edit,
    DiffLocalFileAfterEditInput,
)


def test_diff_local_file_after_edit_success(tmp_path: Path):
    local_file = tmp_path / "local_diff_test.txt"
    original_text = "alpha\nbeta\ngamma"
    local_file.write_text(original_text)

    new_text = "alpha\ndelta\ngamma"
    input_data = DiffLocalFileAfterEditInput(
        file_path=str(local_file), replacement_text=new_text
    )
    result = diff_local_file_after_edit(input_data)

    assert local_file.read_text() == new_text
    assert "-beta" in result
    assert "+delta" in result
