# tests/utils/test_exec_common.py
import subprocess
import types
import pytest

import aegis.utils.exec_common as exec_common


class FakeCP:
    def __init__(self, rc=0, out=b"", err=b""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def test_run_subprocess_list_args_text_mode(monkeypatch):
    captured = {}

    def fake_run(argv, **kwargs):
        # runner should forward list argv and set shell=False
        captured["argv"] = argv
        captured["shell"] = kwargs.get("shell")
        return FakeCP(rc=0, out=b"ok\n", err=b"")

    monkeypatch.setattr(exec_common.subprocess, "run", fake_run, raising=True)

    res = exec_common.run_subprocess(
        ["echo", "ok"],
        timeout=2,
        allow_shell=False,
        text_mode=True,
    )
    assert isinstance(res, FakeCP.__class__) or hasattr(res, "stdout")
    assert captured["argv"] == ["echo", "ok"]
    assert captured["shell"] is False
    # contract: stdout/stderr are bytes when text_mode=True (decoding done by callers)
    assert isinstance(res.stdout, (bytes, bytearray))
    assert res.stdout.strip() == b"ok"


def test_run_subprocess_string_shell(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["shell"] = kwargs.get("shell")
        return FakeCP(rc=0, out=b"", err=b"")

    monkeypatch.setattr(exec_common.subprocess, "run", fake_run, raising=True)

    res = exec_common.run_subprocess(
        "echo hello",
        timeout=1,
        allow_shell=True,
        text_mode=True,
    )
    assert captured["cmd"] == "echo hello"
    assert captured["shell"] is True
    assert res.returncode == 0


def test_run_subprocess_timeout_propagates(monkeypatch):
    def fake_run(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["sleep", "5"], timeout=1)

    monkeypatch.setattr(exec_common.subprocess, "run", fake_run, raising=True)

    with pytest.raises(subprocess.TimeoutExpired):
        exec_common.run_subprocess(
            ["sleep", "5"], timeout=1, allow_shell=False, text_mode=True
        )
