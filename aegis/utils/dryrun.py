# aegis/utils/dryrun.py
"""
Unified dry-run controller.

Supports both legacy callable usage (dry_run()) and the newer property style
(dry_run.enabled), plus a stable preview payload helper used across executors.
Environment:
  AEGIS_DRY_RUN = 1|true|on|yes  -> enables dry-run at process start
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Any, Dict


def _env_truthy(val: str | None) -> bool:
    if not val:
        return False
    return val.strip().lower() in {"1", "true", "on", "yes"}


class _DryRun:
    def __init__(self) -> None:
        self.enabled: bool = _env_truthy(os.getenv("AEGIS_DRY_RUN"))

    # Legacy callable form: dry_run() -> bool
    def __call__(self) -> bool:
        return bool(self.enabled)

    # Programmatic toggle
    def set(self, flag: bool) -> bool:
        self.enabled = bool(flag)
        return self.enabled

    # Standard preview payload used in tests/executors
    def preview_payload(self, *, tool: str, args: Any) -> Dict[str, Any]:
        ts = int(time.time() * 1000)
        try:
            # args can be any JSON-serializable or plain Python structure
            return {"tool": tool, "args": args, "ts_ms": ts}
        except Exception:
            # Fallback if args isn't representable
            return {"tool": tool, "args": "<unserializable>", "ts_ms": ts}

    # Convenience context managers
    @contextmanager
    def activate(self):
        """Temporarily enable dry-run."""
        prev = self.enabled
        self.enabled = True
        try:
            yield
        finally:
            self.enabled = prev

    @contextmanager
    def override(self, flag: bool):
        """Temporarily set dry-run to a specific value."""
        prev = self.enabled
        self.enabled = bool(flag)
        try:
            yield
        finally:
            self.enabled = prev


dry_run = _DryRun()

__all__ = ["dry_run"]
