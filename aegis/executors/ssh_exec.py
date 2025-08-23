# aegis/executors/ssh_exec.py
"""
Provides a centralized, robust client for SSH and SCP operations.

Now interface-aware:
- Accepts a MachineManifest and optional interface_name.
- Resolves address/port from the chosen NetworkInterface.
"""

import shlex
import subprocess
from pathlib import Path
from typing import Tuple, Optional

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.schemas.machine import MachineManifest
from aegis.utils.manifest_resolver import resolve_target_host_port
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time
import re

logger = setup_logger(__name__)


def _sanitize_cli_list(argv: list[str]) -> str:
    """
    Redact sensitive bits for logging: we only log a preview string, not the actual list.
    """
    s = " ".join(shlex.quote(x) for x in argv)
    s = re.sub(r"(-i\s+)(\S+)", r"\1********", s)
    s = re.sub(
        r"(\b(password|passwd|token|api[_-]?key|secret)\s*=\s*)([^ \t]+)",
        r"\1********",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"(Authorization[:=]\s*Bearer\s+)([^\s]+)",
        r"\1********",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"(Cookie[:=]\s*)([^ \t;]+[^ \t]*)", r"\1********", s, flags=re.IGNORECASE
    )
    return s


class SSHExecutor:
    """A robust client for executing commands and transferring files on a remote host."""

    def __init__(
        self,
        manifest: Optional[MachineManifest] = None,
        ssh_target: Optional[str] = None,
        *,
        username: str = "root",
        port: Optional[int] = None,
        private_key_path: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 120,
        interface_name: Optional[str] = None,
    ):
        """
        Initialize the SSH executor with connection details.

        Preferred: provide `manifest` (with interfaces) and optional `interface_name`.
        Back-compat: you may still pass `ssh_target` and `port` directly without a manifest.

        :param manifest: Machine manifest used to resolve interface and target address.
        :type manifest: Optional[MachineManifest]
        :param ssh_target: Direct override for host if no manifest is provided.
        :type ssh_target: Optional[str]
        :param username: SSH username to authenticate as.
        :type username: str
        :param port: SSH port (overrides interface port if provided).
        :type port: Optional[int]
        :param private_key_path: Path to private key (key-based auth).
        :type private_key_path: Optional[str]
        :param password: Password for password-based auth.
        :type password: Optional[str]
        :param timeout: Default timeout in seconds for SSH operations.
        :type timeout: int
        :param interface_name: Logical interface label (e.g., "mgmt0") for provenance.
        :type interface_name: Optional[str]
        """
        self.manifest = manifest
        self.username = username
        self.private_key_path = private_key_path
        self.password = password
        self.default_timeout = timeout

        if manifest:
            address, nic_port, nic_name = resolve_target_host_port(
                manifest, interface_name
            )
            self.ssh_target = address
            self.port = int(port or nic_port or 22)
            self.interface_name = nic_name
        else:
            if not ssh_target:
                raise ConfigurationError(
                    "Either 'manifest' or 'ssh_target' must be provided."
                )
            self.ssh_target = ssh_target
            self.port = int(port or 22)
            self.interface_name = interface_name or "unspecified"

        if not private_key_path and not password:
            logger.warning(
                "No private_key_path or password provided; relying on agent/ssh config."
            )

    def _run_subprocess(
        self, command_list: list[str], timeout: int
    ) -> Tuple[int, str, str]:
        """
        Internal method to execute a subprocess (ssh/scp) with robust error handling.
        """
        try:
            logger.info(f"Running SSH subprocess: {_sanitize_cli_list(command_list)}")
        except Exception:
            logger.info("Running SSH subprocess.")

        try:
            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                encoding="utf-8",
                errors="surrogateescape",
            )
        except subprocess.TimeoutExpired as e:
            logger.error(
                f"SSH command timed out after {timeout} seconds: {_sanitize_cli_list(command_list)}"
            )
            raise ToolExecutionError(
                f"SSH command timed out after {timeout} seconds"
            ) from e
        except Exception as e:
            logger.error(
                f"Error executing SSH command: {_sanitize_cli_list(command_list)} -> {e}"
            )
            raise ToolExecutionError(f"Error executing SSH command: {e}") from e

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        return result.returncode, stdout, stderr

    def run(self, command: str, *, timeout: Optional[int] = None) -> str:
        """
        Run a command over SSH and return stdout. Raises if exit code != 0.
        """
        eff_timeout = timeout or self.default_timeout

        ssh_cmd = [
            "ssh",
            "-p",
            str(self.port),
            f"{self.username}@{self.ssh_target}",
        ]

        if self.private_key_path:
            ssh_cmd += ["-i", self.private_key_path]
        ssh_cmd += ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
        ssh_cmd += ["--", command]

        rc, stdout, stderr = self._run_subprocess(ssh_cmd, eff_timeout)
        if rc != 0:
            logger.error(f"Remote command failed with RC {rc} on {self.ssh_target}.")
            raise ToolExecutionError(
                f"Remote command failed with exit code {rc}. STDERR: {stderr}"
            )
        return stdout

    def upload(
        self, local_path: str, remote_path: str, *, timeout: Optional[int] = None
    ) -> None:
        """
        Upload a file to the remote host via SCP.
        """
        eff_timeout = timeout or self.default_timeout
        scp_cmd = ["scp", "-P", str(self.port)]
        if self.private_key_path:
            scp_cmd += ["-i", self.private_key_path]
        scp_cmd += [local_path, f"{self.username}@{self.ssh_target}:{remote_path}"]

        rc, stdout, stderr = self._run_subprocess(scp_cmd, eff_timeout)
        if rc != 0:
            logger.error(f"SCP upload failed with RC {rc} to {self.ssh_target}.")
            raise ToolExecutionError(
                f"SCP upload failed with exit code {rc}. STDERR: {stderr}"
            )

    def download(
        self, remote_path: str, local_path: str, *, timeout: Optional[int] = None
    ) -> None:
        """
        Download a file from the remote host via SCP.
        """
        eff_timeout = timeout or self.default_timeout
        scp_cmd = ["scp", "-P", str(self.port)]
        if self.private_key_path:
            scp_cmd += ["-i", self.private_key_path]
        scp_cmd += [f"{self.username}@{self.ssh_target}:{remote_path}", local_path]

        rc, stdout, stderr = self._run_subprocess(scp_cmd, eff_timeout)
        if rc != 0:
            logger.error(f"SCP download failed with RC {rc} from {self.ssh_target}.")
            raise ToolExecutionError(
                f"SCP download failed with exit code {rc}. STDERR: {stderr}"
            )

    def check_file_exists(
        self, file_path: str, *, timeout: Optional[int] = None
    ) -> bool:
        """
        Check whether a file exists on the remote machine.
        """
        eff_timeout = timeout or self.default_timeout
        command = f"test -f {shlex.quote(file_path)} && echo '__AEGIS_FILE_EXISTS__'"
        marker_string = "__AEGIS_FILE_EXISTS__"

        try:
            output = self.run(command, timeout=eff_timeout)
            return marker_string in output
        except ToolExecutionError as e:
            if "Remote command failed with exit code" in str(e):
                logger.debug(
                    f"File '{file_path}' does not exist on '{self.ssh_target}' (test -f failed)."
                )
                return False
            else:
                logger.error(
                    f"Error checking file existence for '{file_path}' on '{self.ssh_target}': {e}"
                )
                raise


# === ToolResult wrappers ===
from typing import Optional as _Opt


def _now_ms() -> int:
    return int(time.time() * 1000)


def _error_type_from_exception(e: Exception) -> str:
    msg = str(e).lower()
    if "timeout" in msg:
        return "Timeout"
    if "permission" in msg or "auth" in msg:
        return "Auth"
    if "not found" in msg or "no such" in msg:
        return "NotFound"
    if "parse" in msg or "json" in msg:
        return "Parse"
    return "Runtime"


class SSHExecutorToolResultMixin:
    def run_result(self, command: str, timeout: _Opt[int] = None) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="ssh.exec",
                args=redact_for_log(
                    {
                        "target": self.ssh_target,
                        "iface": self.interface_name,
                        "command": command,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] ssh.exec",
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"preview": preview},
            )
        try:
            out = self.run(command, timeout=timeout)
            return ToolResult.ok_result(
                stdout=out,
                exit_code=0,
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"command": command},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"command": command},
            )

    def upload_result(
        self, local_path: str, remote_path: str, timeout: _Opt[int] = None
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="scp.upload",
                args=redact_for_log(
                    {
                        "target": self.ssh_target,
                        "iface": self.interface_name,
                        "local_path": local_path,
                        "remote_path": remote_path,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] scp.upload",
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"preview": preview},
            )
        try:
            self.upload(local_path, remote_path, timeout=timeout)
            return ToolResult.ok_result(
                stdout="OK",
                exit_code=0,
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"local_path": local_path, "remote_path": remote_path},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"local_path": local_path, "remote_path": remote_path},
            )

    def download_result(
        self, remote_path: str, local_path: str, timeout: _Opt[int] = None
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="scp.download",
                args=redact_for_log(
                    {
                        "target": self.ssh_target,
                        "iface": self.interface_name,
                        "remote_path": remote_path,
                        "local_path": local_path,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] scp.download",
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"preview": preview},
            )
        try:
            self.download(remote_path, local_path, timeout=timeout)
            return ToolResult.ok_result(
                stdout="OK",
                exit_code=0,
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"remote_path": remote_path, "local_path": local_path},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"remote_path": remote_path, "local_path": local_path},
            )

    def check_file_exists_result(
        self, file_path: str, timeout: _Opt[int] = None
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="ssh.test_file",
                args=redact_for_log(
                    {
                        "target": self.ssh_target,
                        "iface": self.interface_name,
                        "path": file_path,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] ssh.test_file",
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"preview": preview},
            )
        try:
            exists = self.check_file_exists(file_path, timeout=timeout)
            return ToolResult.ok_result(
                stdout=str(exists),
                exit_code=0,
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"path": file_path},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                target_host=str(getattr(self, "ssh_target", None)),
                interface=str(getattr(self, "interface_name", None)),
                meta={"path": file_path},
            )


SSHExecutor.run_result = SSHExecutorToolResultMixin.run_result
SSHExecutor.upload_result = SSHExecutorToolResultMixin.upload_result
SSHExecutor.download_result = SSHExecutorToolResultMixin.download_result
SSHExecutor.check_file_exists_result = (
    SSHExecutorToolResultMixin.check_file_exists_result
)
