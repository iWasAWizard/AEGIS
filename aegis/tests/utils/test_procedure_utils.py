# aegis/tests/utils/test_procedure_utils.py
"""Unit tests for the CSV procedure reporting utility."""
from pathlib import Path

import pytest

from aegis.utils.procedure import save_procedure_csv


@pytest.fixture
def mock_state() -> dict:
    """Provides a sample state dictionary for the reporting function."""
    return {"result": [{"command": "c1", "notes": "n1"}, {"command": "c2", "notes": "n2"}]}


def test_save_procedure_csv(mock_state: dict, tmp_path: Path):
    """Verify that a correctly formatted CSV procedure file is created."""
    csv_path = tmp_path / "procedure.csv"
    save_procedure_csv(mock_state, str(csv_path))

    assert csv_path.is_file()
    content = csv_path.read_text()
    lines = content.strip().split('\n')

    assert len(lines) == 3
    assert "Step,Action Taken,Expected Result,Notes" in lines[0]
    assert "1,c1,N/A,n1" in lines[1]
