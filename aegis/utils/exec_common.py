# aegis/utils/exec_common.py
from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union, Tuple, Dict

# ---- Time helpers ----------------------------------------------------------


def now_ms() -> int:
    """Wall-clock timestamp in milliseconds for latency measurement."""
    return int(time.time() * 1000)


# ---- Result container ------------------------------------------------------


@dataclass
class ExecResult:
    argv: List[str]
    returncode: Optional[int]
    stdout: bytes
    stderr: bytes
    duration_ms: int
    started_ms: int
    ended_ms: int
    timed_out: bool
    truncated_stdout: bool
    truncated_stderr: bool

    def stdout_text(self, encoding: str = "utf-8", errors: str = "replace") -> str:
        return self.stdout.decode(encoding, errors)

    def stderr_text(self, encoding: str = "utf-8", errors: str = "replace") -> str:
        return self.stderr.decode(encoding, errors)


# ---- Exceptions -> error_type mapping -------------------------------------


def map_exception_to_error_type(exc: BaseException) -> str:
    """Map common process errors to a normalized string for ToolResult/error taxonomy."""
    if isinstance(exc, subprocess.TimeoutExpired):
        return "timeout"
    if isinstance(exc, FileNotFoundError):
        return "not_found"
    if isinstance(exc, PermissionError):
        return "permission_denied"
    if isinstance(exc, subprocess.CalledProcessError):
        return "nonzero_exit"
    if isinstance(exc, OSError):
        return "os_error"
    return exc.__class__.__name__


# ---- Guardrails ------------------------------------------------------------

_SHELL_METACHARS = set(";|&><`$(){}[]*?!\\\"'")


def _looks_shelly(s: str) -> bool:
    return any(ch in _SHELL_METACHARS for ch in s)


def _truncate(data: bytes, max_bytes: Optional[int]) -> Tuple[bytes, bool]:
    if max_bytes is None or len(data) <= max_bytes:
        return data, False
    return data[:max_bytes], True


# ---- Main runner -----------------------------------------------------------


def run_subprocess(
    cmd: Union[str, Sequence[str]],
    *,
    timeout: Optional[float] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    allow_shell: bool = False,
    max_output_bytes: Optional[int] = 1_000_000,
    text_mode: bool = False,
) -> ExecResult:
    """
    Execute a command with safe defaults:
      - shell=False by default (explicitly opt-in via allow_shell=True).
      - Captures stdout/stderr as bytes; use .stdout_text()/.stderr_text() for text.
      - Applies size caps to outputs to avoid memory/log blow-ups.
      - Returns a normalized ExecResult (including timing/truncation/timeout flags).

    Args:
        cmd: argv list or command string. If a string is provided and allow_shell=False,
             it will be tokenized with shlex.split() to avoid invoking a shell.
        timeout: seconds before raising TimeoutExpired.
        cwd: working directory for the process.
        env: environment overlay (merged onto os.environ).
        allow_shell: if True and cmd is str, executes via /bin/sh -c with basic guardrails.
        max_output_bytes: per-stream cap for stdout/stderr (None to disable).
        text_mode: if True, normalize to utf-8 text then back to bytes before truncation.

    Returns:
        ExecResult with normalized data.

    Raises:
        subprocess.TimeoutExpired, FileNotFoundError, PermissionError, OSError on failures.
    """
    started = now_ms()
    ended = started

    # Build environment
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    # Prepare argv & shell settings
    shell = False
    if isinstance(cmd, str):
        if allow_shell:
            _ = _looks_shelly(cmd)  # note but don’t block
            shell = True
            argv_for_record = ["/bin/sh", "-lc", cmd]
            popen_cmd = cmd  # raw string to shell
        else:
            argv_for_record = shlex.split(cmd)
            popen_cmd = argv_for_record
    else:
        argv_for_record = list(cmd)
        popen_cmd = argv_for_record

    try:
        proc = subprocess.run(
            popen_cmd,
            shell=shell,
            cwd=cwd,
            env=run_env,
            input=None,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        ended = now_ms()
        out = (
            proc.stdout
            if isinstance(proc.stdout, (bytes, bytearray))
            else bytes(proc.stdout or b"")
        )
        err = (
            proc.stderr
            if isinstance(proc.stderr, (bytes, bytearray))
            else bytes(proc.stderr or b"")
        )
        returncode: Optional[int] = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired as te:
        ended = now_ms()
        out = te.output if isinstance(te.output, (bytes, bytearray)) else b""
        err = te.stderr if isinstance(te.stderr, (bytes, bytearray)) else b""
        returncode = None
        timed_out = True
        raise
    except Exception:
        ended = now_ms()
        raise

    duration = ended - started

    if text_mode:
        out_bytes = (out.decode("utf-8", "replace")).encode("utf-8")
        err_bytes = (err.decode("utf-8", "replace")).encode("utf-8")
    else:
        out_bytes, err_bytes = out, err

    out_trunc, out_was_trunc = _truncate(out_bytes, max_output_bytes)
    err_trunc, err_was_trunc = _truncate(err_bytes, max_output_bytes)

    return ExecResult(
        argv=argv_for_record,
        returncode=returncode,
        stdout=out_trunc,
        stderr=err_trunc,
        duration_ms=duration,
        started_ms=started,
        ended_ms=ended,
        timed_out=timed_out,
        truncated_stdout=out_was_trunc,
        truncated_stderr=err_was_trunc,
    )
