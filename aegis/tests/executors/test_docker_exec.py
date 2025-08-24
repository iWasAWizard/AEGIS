# tests/executors/test_docker_exec.py
import json
from pathlib import Path

from aegis.executors.docker_exec import DockerExecutor


def _mk_executor(monkeypatch):
    """
    Create a DockerExecutor without importing/using the real docker SDK.
    We monkeypatch __init__ to avoid daemon access and just attach minimal attrs.
    """

    def fake_init(self, base_url=None, timeout=30):
        self.default_timeout = timeout

    monkeypatch.setattr(DockerExecutor, "__init__", fake_init, raising=True)
    return DockerExecutor()  # type: ignore[call-arg]


def test_pull_image_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "pull_image", lambda **kwargs: None, raising=True)

    res = exe.pull_image_result(name="alpine", tag="latest", auth_config=None)
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout == "ok"
    assert res.meta.get("name") == "alpine"
    assert res.meta.get("tag") == "latest"


def test_pull_image_result_timeout_maps(monkeypatch):
    exe = _mk_executor(monkeypatch)

    class Timeouty(Exception):
        def __str__(self):
            return "request timeout while pulling"

    monkeypatch.setattr(
        exe,
        "pull_image",
        lambda **kwargs: (_ for _ in ()).throw(Timeouty()),
        raising=True,
    )

    res = exe.pull_image_result(name="busybox", tag="1.36")
    assert res.ok is False
    assert res.error_type == "Timeout"
    assert "timeout" in (res.stderr or "").lower()


def test_run_container_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "run_container", lambda **kwargs: "cid123", raising=True)

    res = exe.run_container_result(image="alpine", name="t1")
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout == "cid123"
    assert res.meta.get("image") == "alpine"


def test_stop_container_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "stop_container", lambda **kwargs: None, raising=True)

    res = exe.stop_container_result(container_id="cid123", timeout=5)
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout == "ok"
    assert res.meta.get("id") == "cid123"


def test_exec_in_container_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(
        exe, "exec_in_container", lambda **kwargs: (0, "hello\n", ""), raising=True
    )

    res = exe.exec_in_container_result(
        container_id="cid123", cmd=["/bin/echo", "hello"]
    )
    assert res.ok is True
    assert res.exit_code == 0
    assert (res.stdout or "").strip() == "hello"


def test_exec_in_container_result_nonzero(monkeypatch):
    exe = _mk_executor(monkeypatch)
    # Simulate a failing exec: rc=2, with stderr populated
    monkeypatch.setattr(
        exe, "exec_in_container", lambda **kwargs: (2, "", "boom!"), raising=True
    )

    res = exe.exec_in_container_result(container_id="cid123", cmd=["/bin/false"])
    assert res.ok is False
    assert res.error_type == "Runtime"
    assert "boom" in (res.stderr or "").lower()


def test_copy_to_container_result_success(monkeypatch, tmp_path):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "copy_to_container", lambda **kwargs: None, raising=True)

    src = tmp_path / "x.txt"
    src.write_text("data")
    res = exe.copy_to_container_result(
        container_id="cid123", src_path=str(src), dest_path="/tmp/x.txt"
    )
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout == "ok"
    assert res.meta.get("id") == "cid123"


def test_copy_from_container_result_success(monkeypatch, tmp_path):
    exe = _mk_executor(monkeypatch)
    dest = tmp_path / "out.txt"
    monkeypatch.setattr(exe, "copy_from_container", lambda **kwargs: dest, raising=True)

    res = exe.copy_from_container_result(
        container_id="cid123", src_path="/etc/hosts", dest_dir=str(tmp_path)
    )
    assert res.ok is True
    assert res.exit_code == 0
    assert Path(res.stdout).name == dest.name
    assert res.meta.get("id") == "cid123"
