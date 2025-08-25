# tests/executors/test_docker_exec_toolresult_mapping.py
"""
ToolResult wrapper mapping tests for DockerExecutor without requiring docker SDK.

We monkeypatch instance methods invoked by the *Result wrappers to raise or succeed,
verifying error_type mapping and success envelopes.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from aegis.executors import docker_exec as dexec
from aegis.utils.dryrun import dry_run


class Dummy:
    """Minimal object with methods expected by the *Result mixin."""

    def __init__(self):
        # placeholders; will be monkeypatched per-test
        self.pull_image = lambda **kw: None
        self.run_container = lambda **kw: "abc123"
        self.stop_container = lambda **kw: None
        self.exec_in_container = lambda **kw: (0, "ok\n", "")
        self.copy_to_container = lambda **kw: None
        self.copy_from_container = lambda **kw: "/tmp/x.txt"


def test_pull_image_result_timeout_maps_to_timeout(monkeypatch):
    d = Dummy()
    d.pull_image = lambda **kw: (_ for _ in ()).throw(TimeoutError("timeout"))

    res = dexec.DockerExecutorToolResultMixin.pull_image_result(
        d, name="x", tag="latest", auth_config=None
    )
    assert res.ok is False
    assert res.error_type == "Timeout"
    assert "timeout" in (res.stderr or "").lower()


def test_run_container_result_success(monkeypatch):
    d = Dummy()
    d.run_container = lambda **kw: "cid-777"

    res = dexec.DockerExecutorToolResultMixin.run_container_result(
        d, image="busybox", name="t"
    )
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout == "cid-777"


def test_exec_in_container_result_nonzero_maps_to_runtime(monkeypatch):
    d = Dummy()
    d.exec_in_container = lambda **kw: (2, "oops", "bad")

    res = dexec.DockerExecutorToolResultMixin.exec_in_container_result(
        d, container_id="cid", cmd=["false"]
    )
    assert res.ok is False
    assert res.error_type == "Runtime"
    assert "bad" in (res.stderr or "")


def test_copy_from_container_result_success(monkeypatch, tmp_path):
    d = Dummy()
    d.copy_from_container = lambda **kw: tmp_path / "file.txt"

    res = dexec.DockerExecutorToolResultMixin.copy_from_container_result(
        d, container_id="cid", src_path="/x", dest_dir=str(tmp_path)
    )
    assert res.ok is True
    assert str(tmp_path / "file.txt") in (res.stdout or "")


def test_dry_run_short_circuits(monkeypatch):
    d = Dummy()
    try:
        dry_run.enabled = True
        res = dexec.DockerExecutorToolResultMixin.stop_container_result(
            d, container_id="nope", timeout=1
        )
        assert res.ok is True
        assert res.stdout == "[DRY-RUN] docker.stop"
    finally:
        dry_run.enabled = False
