# aegis/utils/env_report.py
from __future__ import annotations

import os
from typing import Dict
from aegis.utils.logger import setup_logger

# Knobs we introduced in Sprint 1
_KNOBS = [
    "AEGIS_POLICY_DENY_TOOLS",
    "AEGIS_POLICY_REQUIRE_APPROVAL",
    "AEGIS_POLICY_RLMAX_PER_MIN",
    "AEGIS_POLICY_ALLOW_HOSTS",
    "AEGIS_POLICY_ALLOW_INTERFACES",
    "AEGIS_BREAKER_WINDOW_S",
    "AEGIS_BREAKER_THRESHOLD",
    "AEGIS_BREAKER_COOLDOWN_S",
    "AEGIS_REQUIRE_APPROVAL_GOAL_CHANGES",
    "AEGIS_GOAL_EDIT_REQUIRE_REASON",
]

# Common API keys we may want to acknowledge without leaking them
_SENSITIVE_KEYS = [
    "OPENAI_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
]


def _redact(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:2]}…{value[-2:]}"


def collect_env() -> Dict[str, str]:
    """Collects env knobs and selected sensitive keys (redacted)."""
    out: Dict[str, str] = {}
    for k in _KNOBS:
        v = os.getenv(k)
        out[k] = v if v is not None else ""
    for k in _SENSITIVE_KEYS:
        v = os.getenv(k)
        if v:
            out[k] = _redact(v)
    return out


def log_env_knobs(logger=None) -> None:
    """Logs a single structured line with all AEGIS env knobs (redacted where needed)."""
    if logger is None:
        logger = setup_logger(__name__)
    env_map = collect_env()
    logger.info(
        "AEGIS startup env knobs", extra={"event_type": "EnvConfig", "env": env_map}
    )
