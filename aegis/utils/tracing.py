# aegis/utils/tracing.py
"""
Lightweight tracing shim with optional Langfuse integration.

Conventions:
- Span names follow **phase.component** style, e.g.:
    - planner.preselect / planner.plan / planner.repair
    - executor.run
    - verifier.judge
    - wrapper.docker.run / wrapper.compose.up / wrapper.slack.send
- Pass contextual fields as kwargs; they will be redacted for logs and forwarded
  best-effort to Langfuse as input metadata.

Usage:
    from aegis.utils.tracing import span

    with span("wrapper.docker.run", image="nginx:latest", name="web-1"):
        ... your code ...

Behavior:
- Always logs SpanStart / SpanEnd with duration_ms (attrs redacted in logs).
- If LANGFUSE_* keys are present and installation succeeds, initializes a
  Langfuse client once per process. All Langfuse calls are best-effort
  and fully wrapped in try/except so they never break the run.

Env:
- AEGIS_TRACE_SPANS=0 disables span logging entirely.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
from contextlib import contextmanager
import contextvars

from aegis.utils.logger import setup_logger
from aegis.utils.redact import redact_for_log

logger = setup_logger(__name__)

_RUN_ID = contextvars.ContextVar("aegis_run_id", default=None)

# Lazy, best-effort Langfuse client. Never required.
_LF = None
_LF_TRACE_CACHE: Dict[str, Any] = {}


def _init_langfuse_if_available() -> Optional[Any]:
    """Try to initialize a Langfuse client if keys are present; return client or None."""
    global _LF
    if _LF is not None:
        return _LF
    try:
        pk = os.getenv("LANGFUSE_PUBLIC_KEY")
        sk = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST")
        if not (pk and sk):
            return None
        # Optional import; fully guarded
        from langfuse import Langfuse  # type: ignore

        _LF = (
            Langfuse(public_key=pk, secret_key=sk, host=host)
            if host
            else Langfuse(public_key=pk, secret_key=sk)
        )
        logger.info("Langfuse client initialized.", extra={"event_type": "TraceInit"})
        return _LF
    except Exception:
        # Never block if Langfuse isn't installed or init fails
        _LF = None
        return None


def _lf_get_or_create_trace(run_id: Optional[str]) -> Optional[Any]:
    """Fetch or create a Langfuse trace object for the given run_id."""
    try:
        lf = _init_langfuse_if_available()
        if lf is None:
            return None
        if not run_id:
            # Create an ephemeral trace if no id provided
            return lf.trace()
        if run_id in _LF_TRACE_CACHE:
            return _LF_TRACE_CACHE[run_id]
        tr = lf.trace(id=run_id)
        _LF_TRACE_CACHE[run_id] = tr
        return tr
    except Exception:
        return None


@contextmanager
def span(name: str, *, run_id: Optional[str] = None, **attrs: Any):
    """
    Context manager for a tracing span. Always logs start/end; optionally reports to Langfuse.
    Example:
        with span("wrapper.compose.up", run_id=task_id, project_name="app", services=2):
            ...
    """
    # Global off-switch for span logging/telemetry
    if os.getenv("AEGIS_TRACE_SPANS", "1") == "0":
        yield
        return
    start = time.time()
    _token = _RUN_ID.set(run_id)
    safe_attrs = {}

    try:
        # Redact attrs for logs; keep original for Langfuse if available
        safe_attrs = redact_for_log(attrs) if isinstance(attrs, dict) else {}
    except Exception:
        safe_attrs = {}

    logger.info(
        f"Span start: {name}",
        extra={
            "event_type": "SpanStart",
            "span": name,
            "run_id": run_id,
            "attrs": safe_attrs,
        },
    )

    # Best-effort Langfuse span
    _lf_span = None
    _lf_trace = _lf_get_or_create_trace(run_id)
    if _lf_trace is not None:
        try:
            # Different SDK versions may accept different kwargs—guard everything.
            _lf_span = _lf_trace.span(name=name, input=attrs or None)  # type: ignore[attr-defined]
        except Exception:
            _lf_span = None

    try:
        yield
        status = "success"
        error_info = None
    except Exception as e:
        status = "error"
        error_info = {"type": type(e).__name__, "msg": str(e)}
        # Try to report the error; never let it bubble from here
        if _lf_span is not None:
            try:
                _lf_span.update(output=error_info, status_message=str(e))  # type: ignore[attr-defined]
            except Exception:
                pass
        raise
    finally:
        duration_ms = int((time.time() - start) * 1000)

        try:
            _RUN_ID.reset(_token)
        except Exception:
            pass

        logger.info(
            f"Span end: {name}",
            extra={
                "event_type": "SpanEnd",
                "span": name,
                "run_id": run_id,
                "duration_ms": duration_ms,
                "status": status,
            },
        )
        if _lf_span is not None:
            try:
                # Close out the span with timing metadata
                _lf_span.end(
                    output={"duration_ms": duration_ms, "status": status},  # type: ignore[attr-defined]
                )
            except Exception:
                pass


def log_generation(
    *,
    run_id: Optional[str],
    model: Optional[str],
    prompt: Any,
    output: Any,
    usage: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort LLM generation log + optional Langfuse generation."""
    # Fall back to the active span's run_id if none was provided
    if run_id is None:
        try:
            run_id = _RUN_ID.get()
        except Exception:
            run_id = None

    try:
        safe_prompt = redact_for_log(prompt)
        safe_output = redact_for_log(output)
    except Exception:
        safe_prompt, safe_output = prompt, output

    logger.info(
        "LLM generation",
        extra={
            "event_type": "LLMGeneration",
            "run_id": run_id,
            "model": model,
            "usage": usage or {},
            "meta": meta or {},
        },
    )

    try:
        tr = _lf_get_or_create_trace(run_id)
        if tr is None:
            return
        # SDKs differ; this is best-effort and fully guarded.
        gen = tr.generation(  # type: ignore[attr-defined]
            model=model or "unknown",
            input=safe_prompt,
            output=safe_output,
            usage=usage or None,
            metadata=meta or None,
        )
        try:
            gen.end()  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        pass
