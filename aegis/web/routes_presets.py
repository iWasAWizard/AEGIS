"""Routes for listing, retrieving, and interacting with saved agent configuration presets."""

import json
from pathlib import Path

import yaml
from fastapi import APIRouter

from aegis.utils.logger import setup_logger

router = APIRouter()
PRESET_DIR = Path("presets")
logger = setup_logger(__name__)


@router.get("/presets")
def list_presets():
    """
    list_presets.
    :return: Description of return value
    :rtype: Any
    """
    logger.info("→ [routes_presets] Entering list_presets()")
    logger.debug("Listing available items...")
    presets = []
    if not PRESET_DIR.exists():
        return presets
    for file in PRESET_DIR.glob("*.*"):
        if file.suffix in [".yaml", ".yml", ".json"]:
            try:
                text = file.read_text()
                data = (
                    yaml.safe_load(text)
                    if file.suffix in [".yaml", ".yml"]
                    else json.loads(text)
                )
                logger.debug("Processing JSON serialization")
                if isinstance(data, dict):
                    presets.append(
                        {
                            "id": file.stem,
                            "name": data.get("name", file.stem),
                            "description": data.get("description", ""),
                            "config": data.get("config", {}),
                        }
                    )
            except Exception as e:
                logger.exception(f"[routes_presets] Error: {e}")
                presets.append({"id": file.stem, "name": file.stem, "error": str(e)})
    return presets


@router.post("/presets")
def save_preset(payload: dict):
    """
    save_preset.
    :param payload: Description of payload
    :type payload: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("→ [routes_presets] Entering save_preset()")
    preset_id = payload.get("id") or payload.get("name", "unnamed").lower().replace(
        " ", "_"
    )
    name = payload.get("name", preset_id)
    description = payload.get("description", "")
    config = payload.get("config", {})
    PRESET_DIR.mkdir(exist_ok=True)
    path = PRESET_DIR / f"{preset_id}.yaml"
    data = {"name": name, "description": description, "config": config}
    path.write_text(yaml.safe_dump(data))
    logger.debug("Returning API response")
    return {"status": "saved", "path": str(path)}
