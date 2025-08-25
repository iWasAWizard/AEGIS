#!/usr/bin/env python3
"""scripts/extract_provenance_failure.py

Small utility: given a provenance.json file path, locate the first event with
`status == "failure"` and print a compact, machine-friendly summary.

Usage:
    python3 scripts/extract_provenance_failure.py reports/<task_id>/provenance.json

Outputs a single JSON line like:
    {"timestamp":"...","tool_name":"read_remote_file","tool_args":{...},"stderr":"...","exit_code":1}

Returns exit code 0 if a failure was printed, 2 if file not found or JSON error, 1 if no failures found.
"""

import json
import sys
from pathlib import Path


def main(path_str: str) -> int:
    path = Path(path_str)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        print(f"ERROR: failed to read/parse JSON: {e}", file=sys.stderr)
        return 2

    events = data.get("events", []) if isinstance(data, dict) else []
    for ev in events:
        if ev.get("status") == "failure":
            out = {
                "timestamp": ev.get("timestamp"),
                "step_id": ev.get("step_id"),
                "tool_name": ev.get("tool_name"),
                "tool_args": ev.get("tool_args"),
            }
            # best-effort: extract stderr/exit_code from tool_result or observation
            tr = ev.get("tool_result") or {}
            if isinstance(tr, dict):
                # typical shapes
                if "stderr" in tr:
                    out["stderr"] = tr.get("stderr")
                if "exit_code" in tr:
                    out["exit_code"] = tr.get("exit_code")
                if "stdout" in tr and "stderr" not in out:
                    out["stdout"] = tr.get("stdout")

            obs = ev.get("observation")
            if (
                obs
                and "stderr" in out
                and isinstance(obs, str)
                and len(str(obs)) > len(str(out.get("stderr") or ""))
            ):
                # prefer observation if it provides a longer textual error
                out["observation"] = obs
            elif obs and not out.get("stderr"):
                out["observation"] = obs

            print(json.dumps(out, ensure_ascii=False))
            return 0

    # no failures
    print("No failure events found", file=sys.stderr)
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python3 scripts/extract_provenance_failure.py <provenance.json>",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
