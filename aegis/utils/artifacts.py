# aegis/utils/artifacts.py
"""
Minimal artifact store for AEGIS.

- Writes bytes to a stable path: <BASE>/<run_id or session>/<tool>/<ts>-<name>
- Computes SHA256 and size; guesses MIME when reasonable.
- Returns a small metadata record for provenance.

Environment:
  AEGIS_ARTIFACT_DIR        (default: ./artifacts)
  AEGIS_DISABLE_ARTIFACTS   (if set to '1', skips writing; returns None)
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def _base_dir() -> Path:
    return Path(os.environ.get("AEGIS_ARTIFACT_DIR", "./artifacts")).resolve()


def _ts_ms() -> int:
    return int(time.time() * 1000)


def _safe(name: str) -> str:
    # Keep it simple and predictable
    return (
        "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", "+"))[:120]
        or "artifact"
    )


@dataclass
class ArtifactRef:
    path: str
    size_bytes: int
    sha256: str
    mime: Optional[str] = None
    name: Optional[str] = None


def write_blob(
    *,
    run_id: Optional[str],
    tool_name: str,
    preferred_name: str,
    data: bytes,
    subdir: Optional[str] = None,
) -> Optional[ArtifactRef]:
    """
    Write an artifact if allowed. Returns ArtifactRef or None when disabled.
    """
    if os.environ.get("AEGIS_DISABLE_ARTIFACTS", "").strip() == "1":
        return None

    try:
        root = _base_dir()
        rid = run_id or "session"
        tool_dir = _safe(tool_name.replace(".", "_"))
        sub = _safe(subdir) if subdir else None

        outdir = root / _safe(rid) / tool_dir
        if sub:
            outdir = outdir / sub
        outdir.mkdir(parents=True, exist_ok=True)

        # Include a small random hex suffix to avoid rare filename collisions.
        rand_hex = os.urandom(4).hex()
        fname = f"{_ts_ms()}-{_safe(preferred_name)}-{rand_hex}"
        final_path = outdir / fname
        tmp_path = outdir / (fname + ".tmp")

        # Compute SHA first on the provided buffer.
        sha256 = hashlib.sha256(data).hexdigest()

        # Atomic write: write to tmp then replace.
        tmp_path.write_bytes(data)
        os.replace(tmp_path, final_path)

        mime, _ = mimetypes.guess_type(str(final_path))
        return ArtifactRef(
            path=str(final_path),
            size_bytes=len(data),
            sha256=sha256,
            mime=mime,
            name=preferred_name,
        )
    except Exception as e:
        # Never fail the caller due to artifact persistence issues.
        try:
            logger.warning(f"Artifact write failed for {preferred_name}: {e}")
        except Exception:
            pass
        return None
