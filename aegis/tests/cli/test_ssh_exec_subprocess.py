# tests/executors/test_ssh_exec_subprocess.py
"""
Covers the hardened SSH subprocess shim:
- Decodes bytes to text and preserves return code.
- Maps TimeoutExpired to ToolExecutionError.
"""
from __future__ import annotations

import subprocess

import pytest

import aegis.executors.ssh_exec as sexec
from aegis.exceptions import ToolExecutionError
import aegis.utils.exec_common as ex_common


class _Res:
    def __init__(self, rc=0, out=b"", err=b""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def test_wrapper_decodes_bytes_and_returns_tuple(monkeypatch):
    def fake_run(argv, *, timeout, allow_shell, text_mode):
        # SSH/SCP should never allow_shell, and must request text_mode in the shim
        assert allow_shell is False
        assert text_mode is True
        return _Res(0, out=b"ok\n", err=b"")

    monkeypatch.setattr(ex_common, "run_subprocess", fake_run, raising=True)

    rc, out, err = sexec._ssh_executor__run_subprocess_via_common(
        None, ["ssh", "-p", "22", "user@host", "true"], 10
    )
    assert rc == 0
    assert out.strip() == "ok"
    assert err == ""


def test_wrapper_maps_timeout_to_tool_error(monkeypatch):
    def fake_run(argv, *, timeout, allow_shell, text_mode):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    monkeypatch.setattr(ex_common, "run_subprocess", fake_run, raising=True)

    with pytest.raises(ToolExecutionError):
        sexec._ssh_executor__run_subprocess_via_common(
            None, ["ssh", "user@host", "sleep", "5"], 1
        )
