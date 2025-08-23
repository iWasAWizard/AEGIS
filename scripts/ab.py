# scripts/ab.py
#!/usr/bin/env python3
"""
A/B runner skeleton: collect metrics from run JSONL files and compare two result sets.

Usage:
  # Collect metrics for a directory of JSONL runs
  python scripts/ab.py collect --label A --runs path/to/runsA --out resultsA.json
  python scripts/ab.py collect --label B --runs path/to/runsB --out resultsB.json

  # Compare two result JSON files
  python scripts/ab.py compare resultsA.json resultsB.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple


def _load_jsonl(p: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                # skip malformed lines
                continue
    return out


def _run_metrics_from_jsonl(records: List[Dict[str, Any]]) -> Tuple[str, int]:
    """
    Heuristic metrics:
      - status: use the last record with a 'status' field if present, otherwise 'unknown'
      - duration_ms: sum of 'duration_ms' fields if present, else 0
    """
    status = "unknown"
    for rec in reversed(records):
        if isinstance(rec, dict) and "status" in rec:
            status = rec.get("status") or "unknown"
            break
    duration_ms = 0
    for rec in records:
        try:
            duration_ms += int(rec.get("duration_ms", 0) or 0)
        except Exception:
            pass
    return status, duration_ms


def collect(label: str, runs_dir: Path, out_path: Path) -> int:
    runs = sorted([p for p in runs_dir.glob("*.jsonl") if p.is_file()])
    metrics = []
    ok = 0
    total = 0
    durations: List[int] = []
    for p in runs:
        recs = _load_jsonl(p)
        status, dur = _run_metrics_from_jsonl(recs)
        total += 1
        if status == "success":
            ok += 1
        durations.append(dur)
        metrics.append({"file": str(p), "status": status, "duration_ms": dur})
    summary = {
        "label": label,
        "runs": len(metrics),
        "success_rate": (ok / total) if total else 0.0,
        "avg_duration_ms": (sum(durations) / len(durations)) if durations else 0.0,
        "details": metrics,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


def compare(a_path: Path, b_path: Path) -> int:
    a = json.loads(a_path.read_text(encoding="utf-8"))
    b = json.loads(b_path.read_text(encoding="utf-8"))
    delta = {
        "A_label": a.get("label"),
        "B_label": b.get("label"),
        "A_success_rate": a.get("success_rate"),
        "B_success_rate": b.get("success_rate"),
        "delta_success_rate": (b.get("success_rate", 0) or 0)
        - (a.get("success_rate", 0) or 0),
        "A_avg_duration_ms": a.get("avg_duration_ms"),
        "B_avg_duration_ms": b.get("avg_duration_ms"),
        "delta_avg_duration_ms": (b.get("avg_duration_ms", 0) or 0)
        - (a.get("avg_duration_ms", 0) or 0),
    }
    print(json.dumps(delta, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("collect")
    pc.add_argument("--label", required=True)
    pc.add_argument("--runs", type=Path, required=True)
    pc.add_argument("--out", type=Path, required=True)

    cmp_ = sub.add_parser("compare")
    cmp_.add_argument("a", type=Path)
    cmp_.add_argument("b", type=Path)

    args = ap.parse_args()
    if args.cmd == "collect":
        return collect(args.label, args.runs, args.out)
    if args.cmd == "compare":
        return compare(args.a, args.b)
    return 1


if __name__ == "__main__":
    sys.exit(main())
