# aegis/tests/utils/test_config_loader.py
"""
Tests for the configuration and preset loading utilities.
"""
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from aegis.schemas.agent import AgentConfig
from aegis.utils.config_loader import load_agent_config


@pytest.fixture
def presets_dir(tmp_path: Path) -> Path:
    """Creates a temporary 'presets' directory for tests."""
    d = tmp_path / "presets"
    d.mkdir()
    return d


def test_load_valid_profile(presets_dir: Path):
    """Verify that a valid preset file is loaded and parsed correctly."""
    valid_content = {
        "state_type": "aegis.agents.task_state.TaskState",
        "entrypoint": "plan",
        "nodes": [{"id": "plan", "tool": "reflect_and_plan"}],
    }
    (presets_dir / "valid.yaml").write_text(yaml.dump(valid_content))

    config = load_agent_config(profile="valid", raw_config=None, config_file=None)

    assert isinstance(config, AgentConfig)
    assert config.entrypoint == "plan"
    assert len(config.nodes) == 1
    assert config.nodes[0].id == "plan"


def test_load_missing_profile():
    """Verify that loading a non-existent profile raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_agent_config(profile="non_existent_profile")


def test_load_invalid_yaml_file(presets_dir: Path):
    """Verify that a malformed YAML file raises a YAMLError."""
    # This YAML has incorrect indentation
    (presets_dir / "bad.yaml").write_text("entrypoint: plan\n nodes: - id: plan")

    with pytest.raises(yaml.YAMLError):
        load_agent_config(profile="bad")


def test_load_invalid_schema_file(presets_dir: Path):
    """Verify that valid YAML with incorrect schema raises a Pydantic ValidationError."""
    # This content is missing the required 'entrypoint' field for AgentConfig
    invalid_content = {"nodes": [{"id": "plan", "tool": "reflect_and_plan"}]}
    (presets_dir / "invalid_schema.yaml").write_text(yaml.dump(invalid_content))

    # Pydantic will raise a validation error because 'entrypoint' is missing
    with pytest.raises(ValidationError):
        load_agent_config(profile="invalid_schema")
