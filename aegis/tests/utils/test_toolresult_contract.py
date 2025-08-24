# tests/utils/test_toolresult_contract.py
"""
Basic contract checks for ToolResult so executors can rely on a stable shape.
We don't assume exact internals—only surface fields used across wrappers.
"""
from aegis.schemas.tool_result import ToolResult


def test_ok_result_shape_minimal():
    r = ToolResult.ok_result(stdout="x", exit_code=0, latency_ms=5, meta={"a": 1})
    assert hasattr(r, "ok") and r.ok is True
    assert r.exit_code == 0
    assert r.stdout == "x"
    assert r.latency_ms >= 0
    assert isinstance(r.meta, dict)


def test_err_result_shape_minimal():
    r = ToolResult.err_result(
        error_type="Timeout", stderr="boom", latency_ms=7, meta={"b": 2}
    )
    assert hasattr(r, "ok") and r.ok is False
    assert r.error_type == "Timeout"
    assert "boom" in (r.stderr or "")
    assert r.latency_ms >= 0
    assert isinstance(r.meta, dict)
