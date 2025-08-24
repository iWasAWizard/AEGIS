# tests/executors/test_compose_exec.py
import json
import pytest

from aegis.executors.compose_exec import ComposeExecutor
from aegis.utils import dryrun as _dryrun_mod


def _mk_executor(monkeypatch):
    # Avoid touching a real CLI by monkeypatching __init__ and methods directly
    def fake_init(self, compose_cmd=None, default_timeout=10):
        self._compose_cmd = ["docker", "compose"]
        self.default_timeout = default_timeout

    monkeypatch.setattr(ComposeExecutor, "__init__", fake_init, raising=True)
    return ComposeExecutor()  # type: ignore[call-arg]


def test_up_down_results_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "up", lambda **kw: None, raising=True)
    monkeypatch.setattr(exe, "down", lambda **kw: None, raising=True)

    r1 = exe.up_result(project_dir=".", build=True, detach=True)
    assert r1.ok is True and r1.stdout == "ok" and r1.exit_code == 0

    r2 = exe.down_result(project_dir=".")
    assert r2.ok is True and r2.stdout == "ok" and r2.exit_code == 0


def test_ps_result_json_list(monkeypatch):
    exe = _mk_executor(monkeypatch)
    data = [{"Name": "web-1", "State": "running"}]
    monkeypatch.setattr(exe, "ps", lambda **kw: data, raising=True)

    r = exe.ps_result(project_dir=".")
    assert r.ok is True
    assert json.loads(r.stdout) == data
    assert r.meta.get("count") == 1


def test_logs_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "logs", lambda **kw: "web-1 | up\n", raising=True)

    r = exe.logs_result(project_dir=".", services=["web"])
    assert r.ok is True
    assert "web-1" in (r.stdout or "")


def test_error_mapping_auth(monkeypatch):
    exe = _mk_executor(monkeypatch)

    def boom(**kw):
        raise RuntimeError("permission denied: docker socket")

    monkeypatch.setattr(exe, "up", boom, raising=True)
    r = exe.up_result(project_dir=".")
    assert r.ok is False
    assert r.error_type == "Auth"
    assert "permission" in (r.stderr or "").lower()


def test_dry_run_previews(monkeypatch):
    exe = _mk_executor(monkeypatch)
    # enable dry-run with deterministic preview
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", True, raising=False)
    monkeypatch.setattr(
        _dryrun_mod.dry_run,
        "preview_payload",
        lambda **kw: {"tool": kw.get("tool"), "args": kw.get("args")},
        raising=False,
    )

    r_up = exe.up_result(project_dir=".", services=["web"], build=True)
    r_ps = exe.ps_result(project_dir=".")
    r_logs = exe.logs_result(project_dir=".", services=["web"])

    for r, tool in [
        (r_up, "compose.up"),
        (r_ps, "compose.ps"),
        (r_logs, "compose.logs"),
    ]:
        assert r.ok is True
        assert (
            r.stdout
            == f"[DRY-RUN] {tool.split('.')[-1].replace('_', '.') if tool.startswith('compose.') else tool}"
        )
        assert isinstance(r.meta.get("preview"), dict)
        assert r.meta["preview"]["tool"] == tool

    # reset flag to avoid leaking
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", False, raising=False)
