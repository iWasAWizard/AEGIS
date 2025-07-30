# aegis/tests/utils/test_machine_loader.py
"""
Unit tests for the machine configuration loader.
"""
import os
from pathlib import Path
from typing import Iterator

import pytest
import yaml

from aegis.exceptions import ConfigurationError
from aegis.schemas.machine import MachineManifest
from aegis.utils.machine_loader import get_machine


@pytest.fixture(autouse=True)
def clean_machine_loader_cache(monkeypatch):
    """Fixture to reset the machine loader cache before and after each test."""
    # This correctly patches the cache variable in the module where it's defined.
    monkeypatch.setattr("aegis.utils.machine_loader._machine_manifest_cache", None)


@pytest.fixture
def mock_manifest_file(tmp_path: Path) -> Iterator[Path]:
    """Creates a temporary machines.yaml file for testing."""
    manifest_content = {
        "test-linux": {
            "name": "test-linux",
            "ip": "192.168.1.10",
            "platform": "linux",
            "provider": "test",
            "type": "vm",
            "shell": "bash",
            "username": "testuser",
            "password": "testpassword",
        },
        "test-with-secret": {
            "name": "test-with-secret",
            "ip": "192.168.1.11",
            "platform": "linux",
            "provider": "test",
            "type": "vm",
            "shell": "bash",
            "username": "root",
            "password": "${ROOT_PASSWORD}",
        },
        "test-missing-field": {
            "name": "test-missing-field",
            # ip is missing
            "platform": "windows",
            "provider": "test",
            "type": "vm",
            "shell": "powershell",
            "username": "admin",
        },
    }
    manifest_path = tmp_path / "machines.yaml"
    manifest_path.write_text(yaml.dump(manifest_content))
    # Change CWD for the test to find the file
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield manifest_path
    os.chdir(original_cwd)


def test_get_machine_success(mock_manifest_file):
    """Verify that a valid machine configuration is loaded correctly."""
    machine = get_machine("test-linux")
    assert isinstance(machine, MachineManifest)
    assert machine.name == "test-linux"
    assert machine.ip == "192.168.1.10"
    assert machine.username == "testuser"
    assert machine.password == "testpassword"


def test_get_machine_with_secret_substitution(mock_manifest_file, monkeypatch):
    """Verify that environment variable secrets are correctly substituted."""
    # Mock the environment variable that pydantic-settings will load
    monkeypatch.setenv("ROOT_PASSWORD", "supersecret_from_env")

    # Reload settings within the context of the test
    from aegis.schemas import settings
    import importlib

    importlib.reload(settings)

    machine = get_machine("test-with-secret")
    assert machine.password == "supersecret_from_env"


def test_get_machine_not_found(mock_manifest_file):
    """Verify that a ConfigurationError is raised for a non-existent machine."""
    with pytest.raises(
        ConfigurationError, match="Machine 'non-existent-machine' not found"
    ):
        get_machine("non-existent-machine")


def test_get_machine_missing_secret(mock_manifest_file, monkeypatch):
    """Verify a ConfigurationError is raised if a required secret is not in the environment."""
    # Ensure the env var is not set
    monkeypatch.delenv("ROOT_PASSWORD", raising=False)

    # Reload settings to reflect the change
    from aegis.schemas import settings
    import importlib

    importlib.reload(settings)

    with pytest.raises(
        ConfigurationError,
        match="Secret 'ROOT_PASSWORD' for machine 'test-with-secret' not found",
    ):
        get_machine("test-with-secret")


def test_get_machine_invalid_config(mock_manifest_file):
    """Verify a ConfigurationError is raised if a machine config is missing a required field."""
    with pytest.raises(
        ConfigurationError,
        match="Invalid configuration for machine 'test-missing-field'",
    ):
        get_machine("test-missing-field")
