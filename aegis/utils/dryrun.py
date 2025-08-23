# aegis/utils/dryrun.py
"""
Dry-run controller for safe previews.

Import this and check `dry_run.enabled` before executing any side-effecting tool.
Emit a preview record instead of performing the action when enabled.

Environment controls:
    - Set AEGIS_DRY_RUN=1 (or "true"/"yes"/"on") to enable globally at process start.

Typical usage in a step/executor:
    from aegis.utils.dryrun import dry_run

    if dry_run.enabled:
        return ToolResult.ok_result(
            stdout="[DRY-RUN] would execute ssh.exec",
            meta={"preview": {"tool": "ssh.exec", "args": args}},
            target_host=host, interface=iface
        )
    else:
        # real execution...
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict


def _env_truthy(val: str | None) -> bool:
    if val is None:
        return False
    return val.strip().lower() in {"1", "true", "yes", "on", "y"}


@dataclass
class DryRun:
    enabled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def preview_payload(self, *, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Shape a standard preview blob for logs/observability."""
        return {"tool": tool, "args": args, "mode": "dry-run"}

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def set(self, flag: bool) -> None:
        self.enabled = bool(flag)


# Singleton-style instance you can import anywhere.
dry_run = DryRun()

# Initialize from environment (opt-in safe default for new deployments).
if _env_truthy(os.getenv("AEGIS_DRY_RUN")) or _env_truthy(os.getenv("AEGIS_DRYRUN")):
    dry_run.enable()
