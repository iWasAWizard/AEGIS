# aegis/cli/_common.py
"""
Common helpers for CLI command sets.
"""
from __future__ import annotations

from typing import Any, Dict
import json
import cmd2

from aegis.schemas.tool_result import ToolResult


def toolresult_to_jsonable(res: ToolResult) -> Dict[str, Any]:
    """
    Convert a ToolResult-ish object to a plain dict without assuming dataclasses.
    """
    return {
        "ok": getattr(res, "ok", None),
        "exit_code": getattr(res, "exit_code", None),
        "error_type": getattr(res, "error_type", None),
        "stdout": getattr(res, "stdout", None),
        "stderr": getattr(res, "stderr", None),
        "latency_ms": getattr(res, "latency_ms", None),
        "meta": getattr(res, "meta", None) or {},
    }


def print_result(app: cmd2.Cmd, res: ToolResult, as_json: bool) -> None:
    """
    Pretty-print a ToolResult, optionally as JSON.
    """
    if as_json:
        app.poutput(json.dumps(toolresult_to_jsonable(res), indent=2))
        return
    if getattr(res, "ok", False):
        out = getattr(res, "stdout", None)
        if out:
            app.poutput(out)
    else:
        err = getattr(res, "stderr", None) or getattr(res, "stdout", None) or "error"
        app.perror(err)
