# tests/cli/test_entrypoint.py
"""
Entry point tests for aegis.__main__.py

Covers:
- Exit code propagation from one-shot runs via _last_exit_code.
- Intercept flag stripping and --dry-run toggling.
"""
from types import SimpleNamespace

import pytest

import aegis.__main__ as entry


class _FakeShell:
    """Minimal stand-in for AegisShell used by the entrypoint."""

    def __init__(self, rc=0, record=None):
        # the CLI handlers stamp this in real code; we mimic it
        self._last_exit_code = rc
        self._record = record if record is not None else []

    def onecmd_plus_hooks(self, cmd: str):
        # record the command string for assertions
        self._record.append(cmd)
        # simulate the handler having already set the status
        return False

    # cmd2 would call cmdloop() in interactive mode; not used in these tests.
    def cmdloop(self):
        return


def test_main_returns_nonzero_on_failure(monkeypatch):
    """
    Ensure that when a command is executed in one-shot mode,
    the process exit code equals the shell's _last_exit_code.
    """
    recorded = []
    fake = _FakeShell(rc=7, record=recorded)
    monkeypatch.setattr(entry, "AegisShell", lambda: fake)

    rc = entry.main(["compose", "ps", "--bad-flag"])
    assert rc == 7, "Entry point should propagate shell's last exit code"
    assert recorded == ["compose ps --bad-flag"]


def test_main_strips_intercept_flags_and_toggles_dry_run(monkeypatch):
    """
    The --dry-run flag is intercepted by the entrypoint:
    - It should NOT appear in the command string.
    - It should set dry_run.enabled = True (if available).
    """
    # Provide a mutable dry_run stub on the module to avoid importing the real one
    entry.dry_run = SimpleNamespace(enabled=False)

    recorded = []
    fake = _FakeShell(rc=0, record=recorded)
    monkeypatch.setattr(entry, "AegisShell", lambda: fake)

    rc = entry.main(["--dry-run", "compose", "ps", "--json"])
    assert rc == 0
    assert recorded == [
        "compose ps --json"
    ], "Intercept flags must not leak into command"
    assert entry.dry_run.enabled is True, "--dry-run should enable dry-run mode"
