# aegis/utils/config.py
"""
Minimal config loader with caching and gentle fallbacks.

- Reads ./config.yaml if present (YAML optional).
- Merges simple environment overrides (currently: limits.max_stdio_bytes).
- Returns a plain dict so callers can do .get(...) safely.
- Exposes reload_config() for tests.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

_CONFIG_CACHE: Dict[str, Any] | None = None


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    if yaml is None:
        logger.warning("PyYAML not installed; cannot parse %s", path)
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return {}
        return data
    except Exception as e:
        logger.error("Failed to parse %s: %s", path, e)
        return {}


def _apply_env_overrides(cfg: Dict[str, Any]) -> Dict[str, Any]:
    # limits.max_stdio_bytes (used by execute_tool)
    limits = dict(cfg.get("limits") or {})
    try:
        env_val = os.environ.get("AEGIS_MAX_STDIO_BYTES")
        if env_val:
            limits["max_stdio_bytes"] = int(env_val)
    except Exception:
        pass
    if limits:
        cfg["limits"] = limits
    return cfg


def get_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    cfg = _read_yaml(Path("config.yaml"))
    cfg = _apply_env_overrides(cfg)
    _CONFIG_CACHE = cfg
    return _CONFIG_CACHE


def reload_config() -> Dict[str, Any]:
    """Clear cache and reload (primarily for tests)."""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
    return get_config()
