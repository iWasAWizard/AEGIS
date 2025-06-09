# aegis/tests/utils/test_timeline_utils.py
"""Unit tests for the timeline plot generation utility."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aegis.utils.timeline import save_timeline_plot


@pytest.fixture
def mock_state() -> dict:
    """Provides a sample state dictionary for the reporting function."""
    return {"result": [{"duration": 5.5}]}


def test_save_timeline_plot(mock_state: dict, tmp_path: Path, monkeypatch):
    """Verify that the timeline plotting function is called correctly."""
    mock_plt = MagicMock()
    monkeypatch.setattr("aegis.utils.timeline.plt", mock_plt)

    plot_path = tmp_path / "timeline.png"
    save_timeline_plot(mock_state, str(plot_path))

    mock_plt.savefig.assert_called_once_with(str(plot_path))
    mock_plt.close.assert_called_once()
