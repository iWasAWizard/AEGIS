# aegis/tests/utils/test_graph_profile_loader.py
"""
Unit tests for the graph profile loader utility.
"""
from pathlib import Path

import pytest
import yaml

from aegis.utils import graph_profile_loader


@pytest.fixture
def mock_presets_dir(tmp_path: Path, monkeypatch):
    """Creates a temporary presets directory with a sample profile."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    profile_content = {"entrypoint": "start"}
    (presets_dir / "test_profile.yaml").write_text(yaml.dump(profile_content))

    # Monkeypatch the Path object in the loader module
    monkeypatch.setattr(graph_profile_loader, "Path", lambda x: tmp_path / x)


def test_load_agent_graph_config_success(mock_presets_dir):
    """Verify that a valid profile is loaded and parsed correctly."""
    config_data = graph_profile_loader.load_agent_graph_config("test_profile")

    assert isinstance(config_data, dict)
    assert config_data["entrypoint"] == "start"


def test_load_agent_graph_config_not_found(mock_presets_dir):
    """Verify that a FileNotFoundError is raised for a non-existent profile."""
    with pytest.raises(FileNotFoundError):
        graph_profile_loader.load_agent_graph_config("non_existent_profile")
