# aegis/utils/replay_logger.py
"""
Replay/event logger for AEGIS.

- Writes newline-delimited JSON records to: reports/<run_id>/replay.jsonl
- Creates directories on demand.
- Uses flush + fsync for durability (best effort; never raises).
- Tolerates non-JSON-serializable payloads by stringifying.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def _reports_dir() -> Path:
    return Path("reports")


def _safe_jsonable(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        try:
            return str(obj)
        except Exception:
            return "<unserializable>"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    """
    Append a single JSON record + newline. Best-effort durability:
    - open(..., 'a', buffering=1) for line-buffered text
    - flush + os.fsync to reduce data loss on crash
    Never raises; logs errors and returns.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                # fsync may not be available on some platforms; ignore
                pass
    except Exception as e:
        logger.error("Failed to append replay event to %s: %s", path, e)


def log_replay_event(
    run_id: Optional[str], event_type: str, data: Dict[str, Any] | None = None
) -> None:
    """
    Record a structured event for later replay/debugging. Never throws.
    """
    try:
        rid = run_id or "session"
        rec = {
            "run_id": rid,
            "ts_iso": _utc_iso(),
            "event_type": event_type,
            "data": _safe_jsonable(data or {}),
        }
        out = _reports_dir() / rid / "replay.jsonl"
        _append_jsonl(out, rec)
    except Exception as e:
        logger.error("log_replay_event failed: %s", e)
