# aegis/cli/_common.py
"""
Common helpers for AEGIS CLI command sets.

- print_result(app, ToolResult, as_json=False): Consistent rendering for text/JSON.
  Also stamps `app._last_exit_code` so the entrypoint can propagate process status.

This module intentionally has no external dependencies beyond stdlib and ToolResult.
"""
from __future__ import annotations

from typing import Any, Dict
import json
import sys

from aegis.schemas.tool_result import ToolResult


def _tr_to_dict(tr: ToolResult) -> Dict[str, Any]:
    """
    Convert a ToolResult into a JSON-serializable dict without assuming
    implementation details beyond common attributes used across the codebase.
    """

    def g(name: str, default=None):
        return getattr(tr, name, default)

    data: Dict[str, Any] = {
        "ok": bool(g("ok", False)),
        "exit_code": g("exit_code", 0 if g("ok", False) else 1),
        "stdout": g("stdout"),
        "stderr": g("stderr"),
        "error_type": g("error_type"),
        "latency_ms": g("latency_ms"),
        "meta": g("meta"),
    }

    # Opportunistically include common executor provenance fields if present
    for extra in ("target_host", "interface"):
        val = g(extra)
        if val is not None:
            data[extra] = val

    return data


def print_result(app, result: ToolResult, *, as_json: bool = False) -> None:
    """
    Print ToolResult consistently and update the shell's last exit code.

    - When as_json is True: emit a stable JSON envelope.
    - When False: print stdout on success, stderr on failure.
    """
    data = _tr_to_dict(result)
    ok = data["ok"]
    exit_code = int(data.get("exit_code", 0 if ok else 1))

    # Stash the last exit code on the cmd2 application for the entrypoint to read.
    try:
        setattr(app, "_last_exit_code", exit_code)
    except Exception:
        # Avoid breaking CLI printing if the host app is not the expected type.
        pass

    if as_json:
        try:
            app.poutput(json.dumps(data, ensure_ascii=False))
        except Exception:
            # Last-ditch fallback (shouldn't happen)
            app.poutput(str(data))
        return

    if ok:
        out = data.get("stdout")
        if out:
            app.poutput(out)
    else:
        err = data.get("stderr") or "Command failed"
        # Prefer cmd2's stderr path if available
        try:
            app.perror(err)
        except Exception:
            app.poutput(err, end="\n", stream=sys.stderr)
