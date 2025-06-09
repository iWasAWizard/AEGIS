# aegis/tests/utils/test_reporting_utils.py
"""
Unit tests for the various report-saving utilities.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aegis.utils.markdown import save_markdown_report
from aegis.utils.procedure import save_procedure_csv
from aegis.utils.timeline import save_timeline_plot


@pytest.fixture
def mock_state() -> dict:
    """Provides a sample state dictionary for the reporting functions."""
    return {
        "task": "A test task",
        "task_id": "report-test-123",
        "result": [
            {
                "tool": "tool1",
                "command": "command1",
                "stdout": "output1",
                "duration": 5.5,
                "notes": "note1",
            },
            {
                "tool": "tool2",
                "command": "command2",
                "stdout": "output2",
                "duration": 2.1,
                "notes": "note2",
            }
        ]
    }


def test_save_markdown_report(mock_state: dict, tmp_path: Path):
    """Verify that a correctly formatted Markdown report is created."""
    report_path = tmp_path / "report.md"
    save_markdown_report(mock_state, str(report_path))

    assert report_path.is_file()
    content = report_path.read_text()

    assert "**Task:** A test task" in content
    assert "**Tool:** `tool1`" in content
    assert "```\noutput2\n```" in content


def test_save_procedure_csv(mock_state: dict, tmp_path: Path):
    """Verify that a correctly formatted CSV procedure file is created."""
    csv_path = tmp_path / "procedure.csv"
    save_procedure_csv(mock_state, str(csv_path))

    assert csv_path.is_file()
    content = csv_path.read_text()
    lines = content.strip().split('\n')

    assert len(lines) == 3  # Header + 2 data rows
    assert "Step,Action Taken,Expected Result,Notes" in lines[0]
    assert "1,command1,N/A,note1" in lines[1]
    assert "2,command2,N/A,note2" in lines[2]


def test_save_timeline_plot(mock_state: dict, tmp_path: Path, monkeypatch):
    """Verify that the timeline plotting function is called correctly."""
    mock_plt = MagicMock()
    monkeypatch.setattr("aegis.utils.timeline.plt", mock_plt)

    plot_path = tmp_path / "timeline.png"
    save_timeline_plot(mock_state, str(plot_path))

    # We don't check the plot content, just that the save function was called.
    mock_plt.savefig.assert_called_once_with(str(plot_path))
    mock_plt.close.assert_called_once()
