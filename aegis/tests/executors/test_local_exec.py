# tests/executors/test_local_exec.py
import subprocess
import pytest

from aegis.executors.local_exec import LocalExecutor
from aegis.utils import dryrun as _dryrun_mod
from aegis.utils import exec_common as _exec_common_mod


def _mk_executor():
    return LocalExecutor(default_timeout=3)


def test_run_success_no_stderr(monkeypatch):
    exe = _mk_executor()

    # Simulate rc=0 with clean stdout
    monkeypatch.setattr(
        exe,
        "_run_subprocess",
        lambda command, shell, timeout: (0, "hello\n", ""),
        raising=True,
    )

    out = exe.run("echo hello")
    assert out.strip() == "hello"


def test_run_success_with_stderr_merges(monkeypatch):
    exe = _mk_executor()

    # rc=0 but stderr has content -> merged into output with [STDERR] section
    monkeypatch.setattr(
        exe,
        "_run_subprocess",
        lambda command, shell, timeout: (0, "ok", "warn"),
        raising=True,
    )

    out = exe.run("do-thing")
    assert "ok" in out
    assert "[STDERR]" in out
    assert "warn" in out


def test_run_nonzero_raises_toolerror(monkeypatch):
    exe = _mk_executor()

    # Non-zero exit should raise with combined output included in message
    monkeypatch.setattr(
        exe,
        "_run_subprocess",
        lambda command, shell, timeout: (2, "some", "boom"),
        raising=True,
    )

    with pytest.raises(Exception) as ei:
        exe.run("false")
    msg = str(ei.value).lower()
    assert "exit code 2" in msg
    assert "boom" in msg or "some" in msg


def test_run_result_dry_run(monkeypatch):
    exe = _mk_executor()

    # Enable dry-run and make preview predictable
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", True, raising=False)
    monkeypatch.setattr(
        _dryrun_mod.dry_run,
        "preview_payload",
        lambda **kw: {"tool": kw.get("tool"), "args": kw.get("args")},
        raising=False,
    )

    res = exe.run_result("echo SECRET", shell=False, timeout=1)
    assert res.ok is True
    assert res.stdout == "[DRY-RUN] local.exec"
    assert isinstance(res.meta.get("preview"), dict)
    assert res.meta["preview"]["tool"] == "local.exec"

    # Reset for other tests
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", False, raising=False)


def test_run_result_success(monkeypatch):
    exe = _mk_executor()

    monkeypatch.setattr(
        exe,
        "run",
        lambda command, timeout=None, shell=False: "done\n",
        raising=True,
    )

    res = exe.run_result("echo done", shell=False)
    assert res.ok is True
    assert res.exit_code == 0
    assert (res.stdout or "").strip() == "done"
    assert res.meta.get("command")


def test_run_result_timeout_mapping(monkeypatch):
    exe = _mk_executor()

    # Simulate a timeout surfaced as ToolExecutionError with "timeout" in message
    def boom(command, timeout=None, shell=False):
        raise RuntimeError("local command timed out after 3 seconds")

    monkeypatch.setattr(exe, "run", boom, raising=True)

    res = exe.run_result("sleep 5")
    assert res.ok is False
    assert res.error_type == "Timeout"
    assert "timeout" in (res.stderr or "").lower()


def test_run_decodes_bytes_from_runner(monkeypatch):
    """
    Extra coverage: ensure the hardened runner's bytes stdout/stderr are normalized
    to text by LocalExecutor._run_subprocess.
    """

    class R:
        def __init__(self, code=0, out=b"", err=b""):
            self.returncode = code
            self.stdout = out
            self.stderr = err

    def fake_run_subprocess(argv_or_str, **kwargs):
        return R(0, out=b"ok\n", err=b"")

    monkeypatch.setattr(
        _exec_common_mod, "run_subprocess", fake_run_subprocess, raising=True
    )

    exe = _mk_executor()
    out = exe.run("echo ok", shell=False)
    assert out.strip() == "ok"
