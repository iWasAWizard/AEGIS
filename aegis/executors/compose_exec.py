# aegis/executors/compose_exec.py
"""
Docker Compose executor with log redaction and ToolResult wrappers.

This module provides a thin, safe adapter over the Docker Compose CLI. It first
attempts to run `docker compose ...` and falls back to `docker-compose ...` if the
plugin form isn't available. All subprocess execution goes through the shared
hardened runner.

No Compose Python SDK is used here to keep dependencies minimal and behavior
close to the user's local tooling.

Supported ops:
- up
- down
- ps
- logs
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import json
import re

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
from aegis.utils.exec_common import run_subprocess, now_ms as _now_ms

logger = setup_logger(__name__)


def _sanitize_cli_list(argv: List[str]) -> str:
    """
    Redact common sensitive bits for logging without changing argument structure.
    """
    s = " ".join(_shlex_quote(a) for a in argv)
    # Basic token redactions: tokens that look like KEY=SECRET or --token xxx
    s = re.sub(
        r"(\b(password|passwd|token|api[_-]?key|secret)\s*=\s*)([^ \t]+)",
        r"\1********",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"(--password\s+)(\S+)", r"\1********", s, flags=re.IGNORECASE)
    s = re.sub(r"(--token\s+)(\S+)", r"\1********", s, flags=re.IGNORECASE)
    return s


def _shlex_quote(s: str) -> str:
    # Minimal portable quoting for logs only
    if not s:
        return "''"
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


class ComposeExecutor:
    """Wrapper over the Docker Compose CLI with careful subprocess handling."""

    def __init__(
        self, project_dir: str | Path | None = None, default_timeout: int = 120
    ):
        """
        :param project_dir: Working directory for compose commands (defaults to CWD).
        :param default_timeout: Timeout (seconds) for non-follow operations.
        """
        self.project_dir = Path(project_dir) if project_dir else None
        self.default_timeout = int(default_timeout)

    # -------- internal helpers --------

    def _base_cmd_candidates(self) -> List[List[str]]:
        """
        Return candidate argv prefixes to try, in order.
        """
        return [["docker", "compose"], ["docker-compose"]]

    def _compose(
        self,
        sub_args: List[str],
        *,
        timeout: Optional[int] = None,
        allow_follow: bool = False,
    ) -> Tuple[int, bytes, bytes]:
        """
        Execute a compose command using the first working candidate.
        If allow_follow=True (e.g., logs -f), we don't impose a timeout by default.
        """
        t = timeout
        if t is None:
            t = None if allow_follow else self.default_timeout

        last_err: Optional[Exception] = None
        for prefix in self._base_cmd_candidates():
            argv = prefix + sub_args
            try:
                logger.info(f"compose exec: {_sanitize_cli_list(argv)}")
                res = run_subprocess(
                    argv,
                    timeout=t,
                    allow_shell=False,
                    text_mode=False,  # we will decode explicitly
                    cwd=str(self.project_dir) if self.project_dir else None,
                )
                # Normalize to tuple (returncode, stdout, stderr)
                rc = res.returncode if res.returncode is not None else 1
                out = res.stdout or b""
                err = res.stderr or b""
                return rc, out, err
            except FileNotFoundError as e:
                # Try next candidate (e.g., docker-compose not installed or vice versa)
                last_err = e
                continue
            except Exception as e:
                # For other errors (timeout, etc.), fail fast
                last_err = e
                break
        # If we get here, all candidates failed
        if last_err:
            raise ToolExecutionError(
                f"Compose execution failed: {last_err}"
            ) from last_err
        raise ToolExecutionError("Compose execution failed for unknown reasons")

    # -------- public ops --------

    def up(
        self,
        *,
        file: Optional[str] = None,
        profiles: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        build: bool = False,
        detach: bool = True,
        remove_orphans: bool = False,
        pull: Optional[str] = None,  # "always" | "missing" | "never"
        project_name: Optional[str] = None,
        scales: Optional[Dict[str, int]] = None,
        timeout: Optional[int] = None,
    ) -> str:
        args: List[str] = ["up"]
        if detach:
            args.append("-d")
        if build:
            args.append("--build")
        if remove_orphans:
            args.append("--remove-orphans")
        if pull in {"always", "missing", "never"}:
            args += ["--pull", pull]
        if file:
            args += ["-f", file]
        if project_name:
            args += ["-p", project_name]
        for p in profiles or []:
            args += ["--profile", p]
        for svc, n in (scales or {}).items():
            args += ["--scale", f"{svc}={int(n)}"]
        # Services go last
        if services:
            args += list(services)

        rc, out, err = self._compose(args, timeout=timeout)
        if rc != 0:
            raise ToolExecutionError(
                f"compose up failed with exit code {rc}. STDERR: {err.decode('utf-8','replace')}"
            )
        return out.decode("utf-8", "replace")

    def down(
        self,
        *,
        file: Optional[str] = None,
        volumes: bool = False,
        remove_orphans: bool = False,
        project_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        args: List[str] = ["down"]
        if volumes:
            args.append("-v")
        if remove_orphans:
            args.append("--remove-orphans")
        if file:
            args += ["-f", file]
        if project_name:
            args += ["-p", project_name]

        rc, out, err = self._compose(args, timeout=timeout)
        if rc != 0:
            raise ToolExecutionError(
                f"compose down failed with exit code {rc}. STDERR: {err.decode('utf-8','replace')}"
            )
        return out.decode("utf-8", "replace")

    def ps(
        self,
        *,
        file: Optional[str] = None,
        project_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Returns JSON when supported (docker compose ps --format json). If the JSON
        format isn't supported by the local compose version, falls back to text.
        """
        base_args: List[str] = []
        if file:
            base_args += ["-f", file]
        if project_name:
            base_args += ["-p", project_name]

        # Try JSON first
        args_json = ["ps", "--format", "json"] + base_args
        rc, out, err = self._compose(args_json, timeout=timeout)
        if rc == 0:
            return out.decode("utf-8", "replace")

        # Fallback to plain text
        args_txt = ["ps"] + base_args
        rc2, out2, err2 = self._compose(args_txt, timeout=timeout)
        if rc2 != 0:
            raise ToolExecutionError(
                f"compose ps failed with exit code {rc2}. STDERR: {err2.decode('utf-8','replace')}"
            )
        return out2.decode("utf-8", "replace")

    def logs(
        self,
        *,
        services: Optional[List[str]] = None,
        file: Optional[str] = None,
        project_name: Optional[str] = None,
        tail: Optional[int] = None,
        timestamps: bool = False,
        follow: bool = False,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Returns log text. If follow=True, this call may block; pass a timeout if desired.
        """
        args: List[str] = ["logs"]
        if timestamps:
            args.append("-t")
        if tail is not None:
            args += ["--tail", str(int(tail))]
        if follow:
            args.append("-f")
        if file:
            args += ["-f", file]
        if project_name:
            args += ["-p", project_name]
        if services:
            args += list(services)

        rc, out, err = self._compose(args, timeout=timeout, allow_follow=follow)
        if rc != 0:
            raise ToolExecutionError(
                f"compose logs failed with exit code {rc}. STDERR: {err.decode('utf-8','replace')}"
            )
        return out.decode("utf-8", "replace")


# === ToolResult wrappers ===


def _errtype(e: Exception) -> str:
    m = str(e).lower()
    if "timeout" in m:
        return "Timeout"
    if "permission" in m or "denied" in m or "auth" in m:
        return "Auth"
    if "not found" in m or "no such" in m:
        return "NotFound"
    if "parse" in m or "json" in m:
        return "Parse"
    return "Runtime"


class ComposeExecutorToolResultMixin:
    def up_result(
        self,
        *,
        project_dir: str | Path | None = None,
        file: Optional[str] = None,
        profiles: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        build: bool = False,
        detach: bool = True,
        remove_orphans: bool = False,
        pull: Optional[str] = None,
        project_name: Optional[str] = None,
        scales: Optional[Dict[str, int]] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="compose.up",
                args=redact_for_log(
                    {
                        "file": file,
                        "profiles": profiles,
                        "services": services,
                        "build": build,
                        "detach": detach,
                        "remove_orphans": remove_orphans,
                        "pull": pull,
                        "project_name": project_name,
                        "scales": scales,
                        "cwd": str(project_dir) if project_dir else None,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] compose.up",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            exe = ComposeExecutor(project_dir=project_dir)
            out = exe.up(
                file=file,
                profiles=profiles,
                services=services,
                build=build,
                detach=detach,
                remove_orphans=remove_orphans,
                pull=pull,
                project_name=project_name,
                scales=scales,
                timeout=timeout,
            )
            return ToolResult.ok_result(
                stdout=out,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"project_name": project_name, "file": file},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"project_name": project_name, "file": file},
            )

    def down_result(
        self,
        *,
        project_dir: str | Path | None = None,
        file: Optional[str] = None,
        volumes: bool = False,
        remove_orphans: bool = False,
        project_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="compose.down",
                args=redact_for_log(
                    {
                        "file": file,
                        "volumes": volumes,
                        "remove_orphans": remove_orphans,
                        "project_name": project_name,
                        "cwd": str(project_dir) if project_dir else None,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] compose.down",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            exe = ComposeExecutor(project_dir=project_dir)
            out = exe.down(
                file=file,
                volumes=volumes,
                remove_orphans=remove_orphans,
                project_name=project_name,
                timeout=timeout,
            )
            return ToolResult.ok_result(
                stdout=out,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"project_name": project_name, "file": file},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"project_name": project_name, "file": file},
            )

    def ps_result(
        self,
        *,
        project_dir: str | Path | None = None,
        file: Optional[str] = None,
        project_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="compose.ps",
                args=redact_for_log(
                    {
                        "file": file,
                        "project_name": project_name,
                        "cwd": str(project_dir) if project_dir else None,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] compose.ps",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            exe = ComposeExecutor(project_dir=project_dir)
            out = exe.ps(file=file, project_name=project_name, timeout=timeout)
            return ToolResult.ok_result(
                stdout=out,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"project_name": project_name, "file": file},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"project_name": project_name, "file": file},
            )

    def logs_result(
        self,
        *,
        project_dir: str | Path | None = None,
        services: Optional[List[str]] = None,
        file: Optional[str] = None,
        project_name: Optional[str] = None,
        tail: Optional[int] = None,
        timestamps: bool = False,
        follow: bool = False,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="compose.logs",
                args=redact_for_log(
                    {
                        "services": services,
                        "file": file,
                        "project_name": project_name,
                        "tail": tail,
                        "timestamps": timestamps,
                        "follow": follow,
                        "cwd": str(project_dir) if project_dir else None,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] compose.logs",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            exe = ComposeExecutor(project_dir=project_dir)
            out = exe.logs(
                services=services,
                file=file,
                project_name=project_name,
                tail=tail,
                timestamps=timestamps,
                follow=follow,
                timeout=timeout,
            )
            return ToolResult.ok_result(
                stdout=out,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"project_name": project_name, "file": file},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"project_name": project_name, "file": file},
            )


# Bind mixin methods to class (non-destructive append-only style)
ComposeExecutor.up_result = ComposeExecutorToolResultMixin.up_result
ComposeExecutor.down_result = ComposeExecutorToolResultMixin.down_result
ComposeExecutor.ps_result = ComposeExecutorToolResultMixin.ps_result
ComposeExecutor.logs_result = ComposeExecutorToolResultMixin.logs_result
