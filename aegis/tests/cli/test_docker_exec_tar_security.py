# tests/executors/test_docker_exec_tar_security.py
"""
Security tests for Docker tar extraction helpers.

Covers protection against:
- Path traversal via '..'
- Absolute paths (e.g., '/etc/passwd')
- Symlink/hardlink entries

Also verifies a normal, safe extraction works.
"""
from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from aegis.exceptions import ToolExecutionError
import aegis.executors.docker_exec as dexec


def _make_tar_bytes(entries):
    """
    Build a tarball in memory.

    entries: list of dicts like:
      - {"name": "dir/file.txt", "data": b"hello"}
      - {"name": "../escape.txt", "data": b"x"}              # traversal
      - {"name": "/abs.txt", "data": b"x"}                   # absolute
      - {"name": "link", "symlink": True, "target": "/etc/passwd"}  # symlink
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for e in entries:
            name = e["name"]
            if e.get("symlink"):
                info = tarfile.TarInfo(name)
                info.type = tarfile.SYMTYPE
                info.linkname = e.get("target", "")
                info.mode = 0o777
                tar.addfile(info)
            else:
                data = e.get("data", b"")
                bio = io.BytesIO(data)
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, fileobj=bio)
    buf.seek(0)
    return buf.getvalue()


def test_rejects_path_traversal(tmp_path: Path):
    data = _make_tar_bytes(
        [
            {"name": "../evil.txt", "data": b"nope"},
        ]
    )
    with pytest.raises(ToolExecutionError):
        dexec._extract_tar_stream(data, tmp_path)


def test_rejects_absolute_paths(tmp_path: Path):
    data = _make_tar_bytes(
        [
            {"name": "/abs.txt", "data": b"nope"},
        ]
    )
    with pytest.raises(ToolExecutionError):
        dexec._extract_tar_stream(data, tmp_path)


def test_rejects_symlinks(tmp_path: Path):
    data = _make_tar_bytes(
        [
            {"name": "good.txt", "data": b"ok"},
            {"name": "sneaky", "symlink": True, "target": "/etc/passwd"},
        ]
    )
    with pytest.raises(ToolExecutionError):
        dexec._extract_tar_stream(data, tmp_path)


def test_allows_safe_extraction(tmp_path: Path):
    data = _make_tar_bytes(
        [
            {"name": "dir/nested.txt", "data": b"hello"},
            {"name": "file.txt", "data": b"world"},
        ]
    )
    # Should not raise
    dexec._extract_tar_stream(data, tmp_path)
    assert (tmp_path / "dir" / "nested.txt").read_text() == "hello"
    assert (tmp_path / "file.txt").read_text() == "world"
