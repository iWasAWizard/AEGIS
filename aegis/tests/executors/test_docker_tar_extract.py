# tests/executors/test_docker_tar_extract.py
import io
import tarfile
import pytest

from aegis.executors.docker_exec import _extract_tar_stream
from aegis.exceptions import ToolExecutionError


def _build_tar_bytes(entries: dict[str, bytes | str]) -> bytes:
    """
    Build an in-memory tar archive from a dict of {name: content}.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, content in entries.items():
            data = (
                content
                if isinstance(content, (bytes, bytearray))
                else str(content).encode("utf-8")
            )
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))
    buf.seek(0)
    return buf.getvalue()


def test_extract_accepts_iterable_bytes_and_writes_file(tmp_path):
    # Build a simple tar with a safe member
    tar_bytes = _build_tar_bytes({"good.txt": b"ok\n"})

    # Simulate Docker's streamed/chunked response: iterable of bytes
    chunk_size = 7
    chunks = (
        tar_bytes[i : i + chunk_size] for i in range(0, len(tar_bytes), chunk_size)
    )

    dest_dir = tmp_path / "out"
    _extract_tar_stream(chunks, dest_dir)

    f = dest_dir / "good.txt"
    assert f.exists()
    assert f.read_text() == "ok\n"


def test_extract_blocks_path_traversal(tmp_path):
    # Member tries to escape via ..
    bad_tar = _build_tar_bytes({"../escape.txt": "nope"})
    with pytest.raises(ToolExecutionError) as ei:
        _extract_tar_stream(bad_tar, tmp_path / "sandbox")
    # Ensure the error clearly indicates the unsafe path
    assert (
        "unsafe path" in str(ei.value).lower()
        or "refusing to extract" in str(ei.value).lower()
    )
