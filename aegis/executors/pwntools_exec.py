# aegis/executors/pwntools_exec.py
"""
Provides a client for interacting with remote services or local binaries via pwntools.
"""
from __future__ import annotations

from typing import Optional, List, Tuple
from dataclasses import dataclass

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time

logger = setup_logger(__name__)

try:
    from pwn import context, remote, process, cyclic, asm, ELF
    from pwnlib.exception import PwnlibException as _PwnlibException

    PWNLIB_AVAILABLE = True
except ImportError:
    PWNLIB_AVAILABLE = False


@dataclass
class TubeProtocol:
    """A tiny helper to interact with a tube-like interface."""

    tube: any

    def sendline(self, s: str) -> None:
        self.tube.sendline(s.encode("utf-8", "ignore"))

    def recvall(self, timeout: float = 5.0) -> bytes:
        return self.tube.recvall(timeout=timeout)

    def close(self) -> None:
        try:
            self.tube.close()
        except Exception:
            pass


class PwntoolsExecutor:
    """A focused wrapper over pwntools for basic CTF-like interactions."""

    def __init__(self, arch: str = "amd64", os_name: str = "linux"):
        """
        :param arch: Architecture for asm/shellcode helpers (e.g., 'amd64', 'i386').
        :type arch: str
        :param os_name: OS name for pwntools context (e.g., 'linux').
        :type os_name: str
        """
        if not PWNLIB_AVAILABLE:
            raise ToolExecutionError("Pwntools is not installed.")
        try:
            context.clear()
            context.update(arch=arch, os=os_name, timeout=5)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to configure pwntools context: {e}"
            ) from e

    def _connect_remote(self, host: str, port: int) -> TubeProtocol:
        try:
            r = remote(host, port)
            return TubeProtocol(r)
        except _PwnlibException as e:
            raise ToolExecutionError(f"Pwntools remote connection error: {e}") from e
        except Exception as e:
            raise ToolExecutionError(f"Remote connection error: {e}") from e

    def _start_process(
        self, binary_path: str, argv: Optional[List[str]] = None
    ) -> TubeProtocol:
        try:
            argv = argv or []
            p = process([binary_path] + argv)
            return TubeProtocol(p)
        except _PwnlibException as e:
            raise ToolExecutionError(f"Pwntools process start error: {e}") from e
        except Exception as e:
            raise ToolExecutionError(f"Process start error: {e}") from e

    def interact_remote(
        self,
        host: str,
        port: int,
        send_lines: Optional[List[str]] = None,
        recv_until: Optional[str] = None,
        timeout_s: int = 5,
    ) -> Tuple[str, bytes]:
        """
        Connect to a remote service, optionally send lines, and read until a marker or EOF.
        """
        try:
            tube = self._connect_remote(host, port)
            if send_lines:
                for line in send_lines:
                    tube.sendline(line)
            data = b""
            if recv_until:
                end = time.time() + timeout_s
                while time.time() < end:
                    chunk = tube.tube.recv(timeout=0.2)
                    if chunk:
                        data += chunk
                        if recv_until.encode("utf-8", "ignore") in data:
                            break
            else:
                data = tube.recvall(timeout=timeout_s)
            tube.close()
            return ("ok", data)
        except Exception as e:
            raise ToolExecutionError(f"Pwntools interact_remote error: {e}") from e

    def interact_process(
        self,
        binary_path: str,
        argv: Optional[List[str]] = None,
        send_lines: Optional[List[str]] = None,
        recv_until: Optional[str] = None,
        timeout_s: int = 5,
    ) -> Tuple[str, bytes]:
        """
        Start a local process, optionally send lines, and read until a marker or EOF.
        """
        try:
            tube = self._start_process(binary_path, argv=argv)
            if send_lines:
                for line in send_lines:
                    tube.sendline(line)
            data = b""
            if recv_until:
                end = time.time() + timeout_s
                while time.time() < end:
                    chunk = tube.tube.recv(timeout=0.2)
                    if chunk:
                        data += chunk
                        if recv_until.encode("utf-8", "ignore") in data:
                            break
            else:
                data = tube.recvall(timeout=timeout_s)
            tube.close()
            return ("ok", data)
        except Exception as e:
            raise ToolExecutionError(f"Pwntools interact_process error: {e}") from e

    def craft_shellcode(self, arch: str, instructions: List[str]) -> bytes:
        """
        Assemble shellcode for the given arch from instruction strings.
        """
        try:
            with context.local(arch=arch):
                src = "\n".join(instructions)
                return asm(src)
        except Exception as e:
            raise ToolExecutionError(f"Pwntools asm error: {e}") from e

    def generate_cyclic_pattern(self, length: int) -> bytes:
        """
        Generate a cyclic pattern (useful for offset discovery).
        """
        try:
            return cyclic(length)
        except Exception as e:
            raise ToolExecutionError(f"Pwntools cyclic error: {e}") from e

    def inspect_elf(self, path: str) -> dict:
        """
        Inspect an ELF binary and return basic metadata.
        """
        try:
            elf = ELF(path)
            return {
                "arch": elf.get_machine_arch(),
                "bits": elf.elfclass,
                "entry": hex(elf.entry),
                "plt": list(elf.plt.keys()) if elf.plt else [],
                "symbols": list(elf.symbols.keys())[:100],
            }
        except Exception as e:
            raise ToolExecutionError(f"Pwntools ELF inspect error: {e}") from e


# === ToolResult wrappers ===
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


class PwntoolsExecutorToolResultMixin:
    def interact_remote_result(
        self,
        host: str,
        port: int,
        send_lines: list[str] | None = None,
        recv_until: str | None = None,
        timeout_s: int = 5,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="pwntools.interact_remote",
                args=redact_for_log({"host": host, "port": port}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] pwntools.interact_remote",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.interact_remote(
                host=host,
                port=port,
                send_lines=send_lines,
                recv_until=recv_until,
                timeout_s=timeout_s,
            )
            return ToolResult.ok_result(
                stdout=str(out[0]),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"host": host, "port": port},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"host": host, "port": port},
            )

    def interact_process_result(
        self,
        binary_path: str,
        argv: list[str] | None = None,
        send_lines: list[str] | None = None,
        recv_until: str | None = None,
        timeout_s: int = 5,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="pwntools.interact_process",
                args=redact_for_log({"binary_path": binary_path}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] pwntools.interact_process",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.interact_process(
                binary_path=binary_path,
                argv=argv,
                send_lines=send_lines,
                recv_until=recv_until,
                timeout_s=timeout_s,
            )
            return ToolResult.ok_result(
                stdout=str(out[0]),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"binary_path": binary_path},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"binary_path": binary_path},
            )

    def craft_shellcode_result(self, arch: str, instructions: list[str]) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="pwntools.craft_shellcode", args=redact_for_log({"arch": arch})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] pwntools.craft_shellcode",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.craft_shellcode(arch=arch, instructions=instructions)
            return ToolResult.ok_result(
                stdout=out.hex(),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"arch": arch},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"arch": arch},
            )

    def generate_cyclic_pattern_result(self, length: int) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="pwntools.generate_cyclic", args=redact_for_log({"length": length})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] pwntools.generate_cyclic",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.generate_cyclic_pattern(length=length)
            return ToolResult.ok_result(
                stdout=out.decode("latin-1", "ignore"),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"length": length},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"length": length},
            )

    def inspect_elf_result(self, path: str) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="pwntools.inspect_elf", args=redact_for_log({"path": path})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] pwntools.inspect_elf",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.inspect_elf(path=path)
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"path": path},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"path": path},
            )


PwntoolsExecutor.interact_remote_result = (
    PwntoolsExecutorToolResultMixin.interact_remote_result
)
PwntoolsExecutor.interact_process_result = (
    PwntoolsExecutorToolResultMixin.interact_process_result
)
PwntoolsExecutor.craft_shellcode_result = (
    PwntoolsExecutorToolResultMixin.craft_shellcode_result
)
PwntoolsExecutor.generate_cyclic_pattern_result = (
    PwntoolsExecutorToolResultMixin.generate_cyclic_pattern_result
)
PwntoolsExecutor.inspect_elf_result = PwntoolsExecutorToolResultMixin.inspect_elf_result
