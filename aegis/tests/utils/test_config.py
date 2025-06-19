# aegis/tests/utils/test_config.py
"""
Unit tests for the global YAML configuration loader.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from aegis.utils import config


@pytest.fixture(autouse=True)
def clean_config_cache():
    """Fixture to reset the config cache before each test."""
    config._config = None
    yield
    config._config = None


@pytest.fixture
def mock_config_file(tmp_path: Path, monkeypatch):
    """Creates a temporary config.yaml file for testing."""
    config_content = {"paths": {"reports": "test_reports/", "logs": "test_logs/"}}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config_content))

    # Monkeypatch the Path object to look in the temp directory
    monkeypatch.setattr(config.Path, "cwd", lambda: tmp_path)
    # The loader builds the path as 'config.yaml', so we patch the constructor
    monkeypatch.setattr(config, "Path", lambda x: tmp_path / x)


def test_get_config_success(mock_config_file):
    """Verify that get_config reads and parses a valid config.yaml."""
    cfg = config.get_config()
    assert isinstance(cfg, dict)
    assert cfg["paths"]["reports"] == "test_reports/"


def test_get_config_caching(mock_config_file, monkeypatch):
    """Verify that the config is read from file only once and then cached."""
    mock_safe_load = MagicMock(wraps=yaml.safe_load)
    monkeypatch.setattr(yaml, "safe_load", mock_safe_load)

    # First call should trigger a read
    config.get_config()
    assert mock_safe_load.call_count == 1

    # Second call should use the cache
    config.get_config()
    assert mock_safe_load.call_count == 1


def test_get_config_not_found(tmp_path, monkeypatch):
    """Verify that a FileNotFoundError is raised if config.yaml does not exist."""
    # Point to an empty directory
    monkeypatch.setattr(config, "Path", lambda x: tmp_path / x)

    with pytest.raises(FileNotFoundError):
        config.get_config()
