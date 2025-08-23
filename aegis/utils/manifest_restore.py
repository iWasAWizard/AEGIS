# aegis/utils/manifest_store.py
"""
Helpers to load a MachineManifest by ID from disk or an inline dict.

Lookup order for adapters:
1) Use inline `manifest` dict if provided.
2) Else, if `manifest_dir` and `machine_id` are provided, load <machine_id>.json|yaml|yml.
3) Else, require direct `ssh_target`.

Supports JSON and YAML; YAML is optional (only if PyYAML is installed).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from aegis.schemas.machine import MachineManifest
from aegis.exceptions import ConfigurationError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

_YAML_ENABLED = False
try:
    import yaml  # type: ignore

    _YAML_ENABLED = True
except Exception:
    _YAML_ENABLED = False


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not _YAML_ENABLED:
        raise ConfigurationError("YAML manifest requested but PyYAML is not installed.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore


def load_manifest_from_dir(machine_id: str, manifest_dir: str) -> MachineManifest:
    base = Path(manifest_dir)
    candidates = [
        base / f"{machine_id}.json",
        base / f"{machine_id}.yaml",
        base / f"{machine_id}.yml",
    ]
    for p in candidates:
        if p.is_file():
            try:
                if p.suffix == ".json":
                    data = _load_json(p)
                else:
                    data = _load_yaml(p)
                return MachineManifest(**data)
            except Exception as e:
                raise ConfigurationError(f"Failed to load manifest {p}: {e}") from e
    raise ConfigurationError(
        f"No manifest found for '{machine_id}' in '{manifest_dir}' "
        f"(looked for {', '.join(str(c) for c in candidates)})"
    )


def resolve_manifest_or_target(
    *,
    machine_id: Optional[str],
    manifest_dir: Optional[str],
    manifest_inline: Optional[Dict[str, Any]],
    ssh_target: Optional[str],
) -> Tuple[Optional[MachineManifest], Optional[str]]:
    """
    Returns (manifest or None, ssh_target or None).
    Exactly one should be non-None; raises if neither is available.
    """
    if manifest_inline:
        try:
            return MachineManifest(**manifest_inline), None
        except Exception as e:
            raise ConfigurationError(f"Inline manifest invalid: {e}") from e

    if machine_id and manifest_dir:
        return load_manifest_from_dir(machine_id, manifest_dir), None

    if ssh_target:
        return None, ssh_target

    raise ConfigurationError(
        "No manifest/target provided. Provide either (manifest) or (machine_id + manifest_dir) or (ssh_target)."
    )
