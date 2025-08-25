# tests/executors/test_local_exec_dryrun_flag.py
"""
Ensure LocalExecutor.run_result respects the dry_run.enabled flag
and does not attempt to execute commands when enabled.
"""
from __future__ import annotations

import pytest

from aegis.executors.local_exec import LocalExecutor
from aegis.utils import dryrun as _dryrun_mod


def test_run_result_respects_dry_run(monkeypatch):
    exe = LocalExecutor(default_timeout=1)

    # If dry-run is enabled, the path should short-circuit and not call .run()
    called = {"run": False}

    def fake_run(command, timeout=None, shell=False):
        called["run"] = True
        return "should-not-happen"

    monkeypatch.setattr(exe, "run", fake_run, raising=True)
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", True, raising=False)
    monkeypatch.setattr(
        _dryrun_mod.dry_run,
        "preview_payload",
        lambda **kw: {"tool": kw.get("tool"), "args": kw.get("args")},
        raising=False,
    )

    res = exe.run_result("echo secret", shell=False)
    assert res.ok is True
    assert res.stdout == "[DRY-RUN] local.exec"
    assert called["run"] is False

    # cleanup
    monkeypatch.setattr(_dryrun_mod.dry_run, "enabled", False, raising=False)
