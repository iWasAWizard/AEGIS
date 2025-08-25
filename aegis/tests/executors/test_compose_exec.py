# tests/executors/test_compose_exec.py
import types
from pathlib import Path

import pytest

import aegis.executors.compose_exec as cexec
from aegis.exceptions import ToolExecutionError


class _FakeRes:
    def __init__(self, rc=0, out=b"", err=b""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def test_up_builds_expected_argv_and_uses_cwd(monkeypatch, tmp_path: Path):
    seen = {}

    def fake_run(argv, **kw):
        # capture for assertions
        seen["argv"] = list(argv)
        seen["cwd"] = kw.get("cwd")
        seen["timeout"] = kw.get("timeout")
        return _FakeRes(rc=0, out=b"ok")

    monkeypatch.setattr(cexec, "run_subprocess", fake_run, raising=True)

    exe = cexec.ComposeExecutor(project_dir=tmp_path, default_timeout=42)
    out = exe.up(
        file="docker-compose.yaml",
        profiles=["dev", "featA"],
        services=["web", "db"],
        build=True,
        detach=True,
        remove_orphans=True,
        pull="always",
        project_name="proj",
        scales={"web": 3, "worker": 2},
    )

    assert out.strip() == "ok"
    argv = seen["argv"]
    # first two elements are the selected compose binary; we assert subcommand area
    assert "up" in argv
    assert "-d" in argv
    assert "--build" in argv
    assert "--remove-orphans" in argv
    assert ["--pull", "always"][0] in argv
    assert "-f" in argv and "docker-compose.yaml" in argv
    assert "-p" in argv and "proj" in argv
    # profiles
    assert "--profile" in argv and "dev" in argv and "featA" in argv
    # scales
    assert "--scale" in argv and "web=3" in argv and "worker=2" in argv
    # services at the end (not strictly required, but good sanity)
    assert argv[-2:] == ["web", "db"]
    # cwd + timeout
    assert seen["cwd"] == str(tmp_path)
    assert seen["timeout"] == 42


def test_falls_back_to_legacy_docker_compose(monkeypatch):
    calls = []

    def fake_run(argv, **kw):
        calls.append(list(argv))
        if argv[:2] == ["docker", "compose"]:
            raise FileNotFoundError("docker compose not found")
        # legacy works
        return _FakeRes(rc=0, out=b"legacy-ok")

    monkeypatch.setattr(cexec, "run_subprocess", fake_run, raising=True)

    exe = cexec.ComposeExecutor()
    out = exe.ps()
    assert out.strip() == "legacy-ok"

    # first try docker compose, then docker-compose
    assert calls[0][:2] == ["docker", "compose"]
    assert calls[1][0] == "docker-compose"


def test_ps_json_then_fallback_to_plain(monkeypatch):
    calls = []

    def fake_run(argv, **kw):
        calls.append(list(argv))
        # Fail when asking for JSON to trigger fallback
        if "--format" in argv:
            return _FakeRes(rc=2, out=b"", err=b"unsupported")
        return _FakeRes(rc=0, out=b"plain-ok")

    monkeypatch.setattr(cexec, "run_subprocess", fake_run, raising=True)

    exe = cexec.ComposeExecutor()
    out = exe.ps()
    assert out.strip() == "plain-ok"

    # first call had --format json, second was plain
    assert "--format" in calls[0]
    assert calls[1][0] in ("docker", "docker-compose")  # whichever candidate worked
    assert "--format" not in calls[1]


def test_logs_follow_uses_no_timeout(monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["timeout"] = kw.get("timeout")
        return _FakeRes(rc=0, out=b"logs")

    monkeypatch.setattr(cexec, "run_subprocess", fake_run, raising=True)

    exe = cexec.ComposeExecutor(default_timeout=77)
    out = exe.logs(services=["web"], follow=True)  # should not pass a timeout
    assert out == "logs"
    assert seen["timeout"] is None


def test_logs_non_follow_uses_default_timeout(monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["timeout"] = kw.get("timeout")
        return _FakeRes(rc=0, out=b"logs")

    monkeypatch.setattr(cexec, "run_subprocess", fake_run, raising=True)

    exe = cexec.ComposeExecutor(default_timeout=77)
    out = exe.logs(services=["web"], follow=False)
    assert out == "logs"
    assert seen["timeout"] == 77


def test_up_nonzero_exit_raises_with_stderr(monkeypatch):
    def fake_run(argv, **kw):
        return _FakeRes(rc=1, out=b"", err=b"boom")

    monkeypatch.setattr(cexec, "run_subprocess", fake_run, raising=True)

    exe = cexec.ComposeExecutor()
    with pytest.raises(ToolExecutionError) as ei:
        exe.up(services=["web"])
    assert "exit code 1" in str(ei.value).lower()
    assert "boom" in str(ei.value).lower()
