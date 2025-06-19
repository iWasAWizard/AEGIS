# aegis/tests/web/test_routes_presets.py
"""
Unit tests for the preset management API routes.
"""
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from aegis.serve_dashboard import app

client = TestClient(app)


@pytest.fixture
def mock_presets_dir(tmp_path: Path, monkeypatch):
    """Creates a temporary presets directory with sample files for testing."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    # Valid preset
    valid_preset = {
        "name": "Test Preset",
        "description": "A valid test preset.",
        "config": {"entrypoint": "start"},
    }
    (presets_dir / "valid_test.yaml").write_text(yaml.dump(valid_preset))

    # Preset without a name field
    simple_preset = {"description": "A simple preset."}
    (presets_dir / "simple_test.yaml").write_text(yaml.dump(simple_preset))

    # Corrupt preset
    (presets_dir / "corrupt_test.yaml").write_text("name: Bad YAML\n  bad-indent")

    # Monkeypatch the PRESET_DIR constant in the routes module
    monkeypatch.setattr("aegis.web.routes_presets.PRESET_DIR", presets_dir)
    yield presets_dir


def test_list_presets(mock_presets_dir):
    """Test that the list_presets endpoint correctly returns valid and handles corrupt presets."""
    response = client.get("/api/presets")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3

    # Find the entries by id
    valid_entry = next((p for p in data if p["id"] == "valid_test"), None)
    simple_entry = next((p for p in data if p["id"] == "simple_test"), None)
    corrupt_entry = next((p for p in data if p["id"] == "corrupt_test"), None)

    assert valid_entry is not None
    assert valid_entry["name"] == "Test Preset"

    assert simple_entry is not None
    assert simple_entry["name"] == "simple_test"  # Should fallback to id

    assert corrupt_entry is not None
    assert "error" in corrupt_entry


def test_get_preset_config(mock_presets_dir):
    """Test retrieving the full configuration of a specific preset."""
    response = client.get("/api/presets/valid_test")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Preset"
    assert data["config"]["entrypoint"] == "start"


def test_get_preset_config_not_found():
    """Test that a 404 is returned for a non-existent preset."""
    # This test doesn't need the fixture as it's testing the "not found" case
    response = client.get("/api/presets/non_existent_preset")
    assert response.status_code == 404


def test_save_preset(mock_presets_dir):
    """Test successfully saving a new preset via POST request."""
    new_preset_data = {
        "id": "new_preset",
        "name": "My New Preset",
        "description": "A dynamically saved preset.",
        "config": {"entrypoint": "new_start", "nodes": []},
    }

    response = client.post("/api/presets", json=new_preset_data)
    assert response.status_code == 200

    # Verify the file was created
    new_file_path = mock_presets_dir / "new_preset.yaml"
    assert new_file_path.is_file()

    # Verify the content is correct
    with new_file_path.open("r") as f:
        saved_data = yaml.safe_load(f)
    assert saved_data["name"] == "My New Preset"
    assert saved_data["config"]["entrypoint"] == "new_start"


def test_save_preset_no_id(mock_presets_dir):
    """Test that saving a preset without an ID or name fails with a 400 error."""
    bad_preset_data = {"description": "This preset is missing a name/id."}
    response = client.post("/api/presets", json=bad_preset_data)
    assert response.status_code == 400
    assert "must have an 'id' or 'name'" in response.json()["detail"]
