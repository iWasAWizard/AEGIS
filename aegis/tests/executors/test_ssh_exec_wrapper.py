# tests/executors/test_ssh_exec_wrappers.py
import pytest
from aegis.executors.ssh_exec import SSHExecutor


def _mk():
    # construct with dummy direct target so manifest is not needed
    return SSHExecutor(ssh_target="example.invalid", username="root", timeout=3)


def test_run_result_success(monkeypatch):
    exe = _mk()
    monkeypatch.setattr(
        exe, "_run_subprocess", lambda argv, timeout: (0, "ok\n", ""), raising=True
    )
    res = exe.run_result("echo ok")
    assert res.ok is True
    assert res.exit_code == 0
    assert (res.stdout or "").strip() == "ok"


def test_run_result_nonzero(monkeypatch):
    exe = _mk()
    # remote non-zero: merged stderr should be surfaced in ToolResult.err_result
    monkeypatch.setattr(
        exe, "_run_subprocess", lambda argv, timeout: (2, "oops", "bad"), raising=True
    )
    res = exe.run_result("false")
    assert res.ok is False
    assert res.error_type == "Runtime"
    assert "oops" in (res.stderr or "") and "bad" in (res.stderr or "")
