# aegis/web/routes_presets.py
"""Routes for listing, retrieving, and interacting with saved agent configuration presets."""

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from aegis.utils.logger import setup_logger

router = APIRouter()
PRESET_DIR = Path("presets")
logger = setup_logger(__name__)


@router.get("/presets", tags=["Presets"])
def list_presets() -> list[dict]:
    """Lists all available agent configuration presets from the 'presets' directory.

    This endpoint scans for YAML files in the `presets/` directory, parses them,
    and returns a list of metadata for each, including its ID, name, and
    description. This is used to populate selection dropdowns in the UI.

    :return: A list of preset metadata objects.
    :rtype: list
    """
    logger.info("Request received to list all presets.")
    presets = []
    if not PRESET_DIR.exists():
        logger.warning(f"Presets directory not found at '{PRESET_DIR}'.")
        return presets

    for file in sorted(PRESET_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                presets.append({
                    "id": file.stem,
                    "name": data.get("name", file.stem),
                    "description": data.get("description", "No description."),
                })
        except (yaml.YAMLError, Exception) as e:
            logger.error(f"Failed to load or parse preset '{file.name}': {e}")
            presets.append({"id": file.stem, "name": file.stem, "error": str(e)})
    logger.info(f"Found {len(presets)} presets.")
    return presets


@router.post("/presets", tags=["Presets"])
def save_preset(payload: dict):
    """Saves a preset configuration to a YAML file in the 'presets' directory.

    This endpoint is used by the UI's preset editor to create or update agent
    behavior configurations.

    :param payload: The preset data, including id, name, description, and config.
    :type payload: dict
    :return: A status message indicating the result.
    :rtype: dict
    :raises HTTPException: If the payload is invalid or cannot be saved.
    """
    preset_id = payload.get("id") or payload.get("name", "unnamed").lower().replace(" ", "_")
    logger.info(f"Request to save preset with ID: '{preset_id}'")

    if not preset_id:
        raise HTTPException(status_code=400, detail="Preset must have an 'id' or 'name'.")

    PRESET_DIR.mkdir(exist_ok=True)
    path = PRESET_DIR / f"{preset_id}.yaml"

    try:
        # Re-structure the payload to be saved
        data_to_save = {
            "name": payload.get("name"),
            "description": payload.get("description"),
            **payload.get("config", {})  # Unpack the config dict
        }
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data_to_save, f, indent=2, default_flow_style=False)
        logger.info(f"Preset '{preset_id}' saved successfully to '{path}'.")
    except Exception as e:
        logger.exception(f"Failed to serialize or write preset '{preset_id}' to file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save preset: {e}")

    return {"status": "saved", "path": str(path)}


@router.get("/presets/{preset_id}", tags=["Presets"])
def get_preset_config(preset_id: str):
    """Retrieves the full configuration content of a specific preset file.

    :param preset_id: The ID (filename without extension) of the preset to fetch.
    :type preset_id: str
    :return: The parsed YAML content of the preset file.
    :rtype: dict
    :raises HTTPException: If the preset file is not found.
    """
    logger.info(f"Request to fetch config for preset: {preset_id}")
    path = PRESET_DIR / f"{preset_id}.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found.")

    try:
        config_data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return config_data
    except Exception as e:
        logger.exception(f"Error reading preset file {path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading preset file: {e}")
