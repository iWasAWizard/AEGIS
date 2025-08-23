# aegis/utils/provenance.py
"""
Tamper-evident provenance ledger (hash-chained JSONL).

Each appended step is recorded as a JSON object with a `curr_hash` derived from:
    SHA256(prev_hash || canonical_json_without_hashes)

Environment:
    - AEGIS_PROVENANCE_PATH: target file path (default: ./provenance.log.jsonl)

Usage:
    from aegis.utils import provenance
    provenance.record_step(
        run_id=state.task_id,
        step_index=len(state.history),
        tool=plan.tool_name,
        tool_args=plan.tool_args,
        target_host=target_host,
        interface=interface,
        status=status,
        observation=observation,
        duration_ms=int(duration_ms),
    )
"""

from __future__ import annotations

import os
import io
import json
import hashlib
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8", "ignore"))
    return h.hexdigest()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


@dataclass
class StepRecord:
    run_id: str
    step_index: int
    utc_ts: str
    tool: str
    args_hash: str
    target_host: Optional[str]
    interface: Optional[str]
    status: str
    observation_hash: str
    duration_ms: int
    prev_hash: str
    curr_hash: str


class _Ledger:
    """Append-only JSONL ledger with a rolling hash chain."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.getenv("AEGIS_PROVENANCE_PATH", "provenance.log.jsonl")
        # In-memory tail hash; also recovered lazily from file when needed
        self._tail_hash: str = "GENESIS"
        self._tail_loaded = False
        self._lock = threading.Lock()

    def _ensure_tail_loaded(self) -> None:
        if self._tail_loaded:
            return
        self._tail_loaded = True
        try:
            if not os.path.exists(self.path):
                return
            last_line = None
            with open(self.path, "rb") as f:
                # Efficiently read last non-empty line
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                buf = bytearray()
                while pos > 0:
                    pos -= 1
                    f.seek(pos)
                    ch = f.read(1)
                    if ch == b"\n":
                        if buf:
                            break
                        continue
                    buf.extend(ch)
                if buf:
                    last_line = bytes(reversed(buf)).decode("utf-8", "ignore")
            if last_line:
                obj = json.loads(last_line)
                self._tail_hash = obj.get("curr_hash", "GENESIS")
        except Exception:
            # Fail open: keep GENESIS
            self._tail_hash = "GENESIS"

    def _open_for_append(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        # Use text mode with explicit utf-8 and line buffering
        return open(self.path, "a", encoding="utf-8")

    def append(self, rec: Dict[str, Any]) -> StepRecord:
        with self._lock:
            self._ensure_tail_loaded()

            # Build unsigned payload (no prev/curr) deterministically
            unsigned = {
                k: v for k, v in rec.items() if k not in ("prev_hash", "curr_hash")
            }
            prev_hash = self._tail_hash
            material = _canonical_json({"prev_hash": prev_hash, **unsigned})
            curr_hash = _sha256(material)

            full = {
                **unsigned,
                "prev_hash": prev_hash,
                "curr_hash": curr_hash,
            }
            step = StepRecord(**full)  # type: ignore[arg-type]

            # Append line
            try:
                with self._open_for_append() as fh:
                    fh.write(_canonical_json(asdict(step)))
                    fh.write("\n")
                    fh.flush()
                self._tail_hash = curr_hash
            except Exception:
                # If write fails, do not update in-memory tail
                pass

            return step


# Singleton ledger
_ledger = _Ledger()


def set_ledger_path(path: str) -> None:
    """Override the ledger file path programmatically (optional)."""
    global _ledger
    _ledger = _Ledger(path)


def record_step(
    *,
    run_id: str,
    step_index: int,
    tool: str,
    tool_args: Dict[str, Any] | None,
    target_host: Optional[str],
    interface: Optional[str],
    status: str,
    observation: str,
    duration_ms: int,
) -> StepRecord:
    """
    Compute hashes and append a step to the ledger.
    """
    args_hash = _sha256(_canonical_json(tool_args or {}))
    observation_hash = _sha256(observation or "")
    rec = {
        "run_id": run_id,
        "step_index": step_index,
        "utc_ts": _utc_now_iso(),
        "tool": tool,
        "args_hash": args_hash,
        "target_host": target_host,
        "interface": interface,
        "status": status,
        "observation_hash": observation_hash,
        "duration_ms": duration_ms,
        # prev_hash/curr_hash are set inside append()
    }
    return _ledger.append(rec)
