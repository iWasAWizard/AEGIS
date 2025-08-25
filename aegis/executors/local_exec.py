# aegis/executors/local_exec.py
"""
Provides a client for executing local shell commands.
"""
import shlex
import subprocess
from typing import Tuple, Optional

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time
import re
from aegis.utils.exec_common import run_subprocess as _safe_run_subprocess

logger = setup_logger(__name__)


def _sanitize_cli(command_str: str) -> str:
    """
    Best-effort redaction of sensitive tokens inside a shell command string.
    We don't attempt full shell parsing—just mask common leak patterns.
    """
    s = command_str

    # --password <val>   or   -p <val>
    s = re.sub(r"(--password\s+)(\S+)", r"\1********", s, flags=re.IGNORECASE)
    s = re.sub(r"(-p\s+)(\S+)", r"\1********", s)

    # password=val, passwd=val, token=val, api_key=val, secret=val
    s = re.sub(
        r"(\b(password|passwd|token|api[_-]?key|secret)\s*=\s*)([^ \t]+)",
        r"\1********",
        s,
        flags=re.IGNORECASE,
    )

    # Authorization: Bearer <token>
    s = re.sub(
        r"(Authorization[:=]\s*Bearer\s+)([^\s]+)",
        r"\1********",
        s,
        flags=re.IGNORECASE,
    )

    # Cookie: bigblob
    s = re.sub(
        r"(Cookie[:=]\s*)([^ \t;]+[^ \t]*)", r"\1********", s, flags=re.IGNORECASE
    )

    # private key inline (very naive)
    s = re.sub(r"(--private-key\s+)(\S+)", r"\1********", s, flags=re.IGNORECASE)

    return s


class LocalExecutor:
    """A client for executing local shell commands consistently."""

    def __init__(self, default_timeout: int = 120):
        """
        Initialize the LocalExecutor.

        :param default_timeout: Default timeout in seconds for subprocess commands.
        :type default_timeout: int
        """
        self.default_timeout = default_timeout

    def _run_subprocess(
        self, command_str: str, shell: bool, timeout: int
    ) -> Tuple[int, str, str]:
        """
        Private helper to run a subprocess command and capture its output.

        :param command_str: The command string to execute.
        :type command_str: str
        :param shell: Whether to use the system shell.
        :type shell: bool
        :param timeout: Timeout in seconds for the command.
        :type timeout: int
        :return: A tuple of (returncode, stdout, stderr).
        :rtype: Tuple[int, str, str]
        """

        # Use hardened shared runner; preserve original API (rc, stdout, stderr)
        try:
            if not shell:
                # If not using shell, tokenize so semantics remain the same
                argv = shlex.split(command_str)
                res = _safe_run_subprocess(
                    argv, timeout=timeout, allow_shell=False, text_mode=True
                )
            else:
                # Caller explicitly requested shell semantics—opt in
                res = _safe_run_subprocess(
                    command_str, timeout=timeout, allow_shell=True, text_mode=True
                )
        except subprocess.TimeoutExpired as e:
            logger.error(
                f"Local command timed out after {timeout} seconds: {_sanitize_cli(command_str)}"
            )
            raise ToolExecutionError(
                f"Local command timed out after {timeout} seconds"
            ) from e

        # Map back to prior tuple contract
        rc = res.returncode if res.returncode is not None else 1
        stdout = res.stdout.decode("utf-8", "replace")
        stderr = res.stderr.decode("utf-8", "replace")
        return rc, stdout, stderr

    def run(
        self, command: str, *, timeout: Optional[int] = None, shell: bool = False
    ) -> str:
        """
        Execute a command and return combined stdout (and stderr on failure).

        :param command: The command to run.
        :type command: str
        :param timeout: Optional timeout in seconds. Defaults to instance's default_timeout.
        :type timeout: Optional[int]
        :param shell: Whether to execute via system shell. Defaults to False.
        :type shell: bool
        :return: Combined stdout (and stderr on failure).
        :rtype: str
        :raises ToolExecutionError: On non-zero exit or execution failure.
        """
        eff_timeout = timeout or self.default_timeout
        rc, stdout, stderr = self._run_subprocess(command, shell, eff_timeout)

        combined_output = stdout
        if stderr:
            combined_output = f"{stdout}\n[STDERR]\n{stderr}".strip()

        if rc != 0:
            logger.error(
                f"Local command '{_sanitize_cli(command)}' failed with RC {rc}."
            )
            raise ToolExecutionError(
                f"Local command failed with exit code {rc}. Output: {combined_output}"
            )

        return combined_output


# === ToolResult wrappers ===
from typing import Optional


def _now_ms() -> int:
    return int(time.time() * 1000)


def _error_type_from_exception(e: Exception) -> str:
    msg = str(e).lower()
    if "timeout" in msg:
        return "Timeout"
    if "permission" in msg or "auth" in msg:
        return "Auth"
    if "not found" in msg or "no such file" in msg:
        return "NotFound"
    if "parse" in msg or "json" in msg:
        return "Parse"
    return "Runtime"


class LocalExecutorToolResultMixin:
    def run_result(
        self,
        command: str,
        *,
        timeout: Optional[int] = None,
        shell: bool = False,
    ) -> ToolResult:
        start = _now_ms()

        # Dry-run path returns a preview rather than executing
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="local.exec",
                args=redact_for_log(
                    {
                        "cmd": _sanitize_cli(command),
                        "shell": shell,
                        "timeout": timeout,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] local.exec",
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )

        try:
            out = self.run(command, timeout=timeout, shell=shell)
            return ToolResult.ok_result(
                stdout=out,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"command": _sanitize_cli(command), "shell": shell},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"command": _sanitize_cli(command), "shell": shell},
            )


LocalExecutor.run_result = LocalExecutorToolResultMixin.run_result
