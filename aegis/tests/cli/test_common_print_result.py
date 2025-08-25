# tests/cli/test_common_print_result.py
"""
Tests for aegis.cli._common.print_result:
- Stamps _last_exit_code on the shell app.
- Renders JSON envelope when requested.
- Prints stderr via perror on errors (text mode).
"""
from __future__ import annotations

import json

from aegis.cli._common import print_result
from aegis.schemas.tool_result import ToolResult


class _App:
    def __init__(self):
        self._last_exit_code = None
        self._out = []
        self._err = []

    def poutput(self, s, **_):
        self._out.append(s)

    def perror(self, s):
        self._err.append(s)


def test_print_result_json_and_exit_code_stamp():
    app = _App()
    tr = ToolResult.ok_result(stdout="hello", exit_code=0, latency_ms=1)
    print_result(app, tr, as_json=True)

    assert app._last_exit_code == 0
    assert len(app._out) == 1
    payload = json.loads(app._out[0])
    assert payload["ok"] is True
    assert payload["stdout"] == "hello"
    assert payload["exit_code"] == 0


def test_print_result_error_path_uses_perror_and_sets_nonzero():
    app = _App()
    tr = ToolResult.err_result(error_type="Runtime", stderr="boom", latency_ms=2)
    print_result(app, tr, as_json=False)

    assert app._last_exit_code == 1
    assert app._err and "boom" in app._err[0]
