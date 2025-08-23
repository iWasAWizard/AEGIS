#!/usr/bin/env python3
"""
Minimal golden trace helper.
- record: copy a run JSONL to a golden file
- verify: diff two JSONL runs on key fields (step index, tool, success, exit_code)
"""
import argparse, json, sys, shutil
from pathlib import Path

KEYS = ("tool", "status", "observation")  # adapt if you log exit_code in observation


def load_jsonl(p: Path):
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield i, json.loads(line)
            except Exception as e:
                raise SystemExit(f"{p}:{i}: invalid JSONL: {e}")


def record(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"Recorded golden: {dst}")


def verify(a: Path, b: Path, limit: int = 20):
    diffs = 0
    for (ia, ra), (ib, rb) in zip(load_jsonl(a), load_jsonl(b)):
        for k in KEYS:
            va = ra.get(k)
            vb = rb.get(k)
            if va != vb:
                print(
                    f"step={ra.get('step_index','?')} key={k}\n  A: {va}\n  B: {vb}\n"
                )
                diffs += 1
                if diffs >= limit:
                    print(f"...stopping at {limit} diffs")
                    return 1
    print("No diffs detected.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record")
    rec.add_argument("src", type=Path)
    rec.add_argument("dst", type=Path)

    ver = sub.add_parser("verify")
    ver.add_argument("golden", type=Path)
    ver.add_argument("candidate", type=Path)
    ver.add_argument("--limit", type=int, default=20)

    args = ap.parse_args()
    if args.cmd == "record":
        record(args.src, args.dst)
        return 0
    if args.cmd == "verify":
        return verify(args.golden, args.candidate, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
