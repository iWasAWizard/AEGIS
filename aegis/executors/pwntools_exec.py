# aegis/executors/pwntools_exec.py
"""
Provides a client for executing pwntools-based interactions.
"""
from typing import Callable, Any, Optional, Protocol, runtime_checkable, cast

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# Import pwntools conditionally for the executor
try:
    from pwn import (
        remote as pwn_remote,
        process as pwn_process,
        context as pwn_context,
        shellcraft as pwn_shellcraft,
        ELF as pwn_ELF,
        cyclic as pwn_cyclic,
        cyclic_find as pwn_cyclic_find,
    )
    from pwnlib.exception import PwnlibException

    PWNTOOLS_AVAILABLE_FOR_EXECUTOR = True
except ImportError:
    PWNTOOLS_AVAILABLE_FOR_EXECUTOR = False

    class PwnlibException(Exception):
        pass


@runtime_checkable
class TubeProtocol(Protocol):
    """Defines the interface for a pwntools-like tube object."""

    def sendline(self, data: bytes): ...
    def recvall(self, timeout: Any = ...) -> bytes: ...
    def close(self): ...

    timeout: int


class PwntoolsExecutor:
    """
    A client for managing pwntools connections (remote, process) and interactions.
    Ensures connections are properly closed.
    """

    def __init__(self, default_timeout: int = 5):
        """
        Initializes the PwntoolsExecutor.

        :param default_timeout: Default timeout in seconds for connection/receive operations.
        :type default_timeout: int
        """
        if not PWNTOOLS_AVAILABLE_FOR_EXECUTOR:
            raise ToolExecutionError(
                "Pwntools library is not installed. Cannot use PwntoolsExecutor."
            )
        self.default_timeout = default_timeout

    def _connect_remote(
        self, host: str, port: int, timeout: Optional[int]
    ) -> TubeProtocol:
        """Establishes a pwntools remote connection."""
        effective_timeout = timeout if timeout is not None else self.default_timeout
        logger.debug(
            f"PwntoolsExecutor: Connecting to remote {host}:{port} with timeout {effective_timeout}s"
        )
        try:
            conn = pwn_remote(host, port, timeout=effective_timeout)
            return conn  # type: ignore
        except PwnlibException as e:
            logger.error(f"Pwntools remote connection to {host}:{port} failed: {e}")
            raise ToolExecutionError(
                f"Pwntools remote connection to {host}:{port} failed: {e}"
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error during pwntools remote connection to {host}:{port}"
            )
            raise ToolExecutionError(f"Unexpected error connecting with pwntools: {e}")

    def _start_process(
        self, executable_path: str, timeout: Optional[int]
    ) -> TubeProtocol:
        """Starts a local process using pwntools."""
        effective_timeout = timeout if timeout is not None else self.default_timeout
        logger.debug(
            f"PwntoolsExecutor: Starting process {executable_path} (ops timeout {effective_timeout}s)"
        )
        try:
            proc = pwn_process(executable_path)
            proc.timeout = effective_timeout
            return proc  # type: ignore
        except FileNotFoundError:
            logger.error(
                f"Executable not found for Pwntools process: '{executable_path}'"
            )
            raise ToolExecutionError(
                f"Pwntools process: Executable not found at '{executable_path}'"
            )
        except PwnlibException as e:
            logger.error(f"Pwntools starting process '{executable_path}' failed: {e}")
            raise ToolExecutionError(
                f"Pwntools process start failed for '{executable_path}': {e}"
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error starting Pwntools process '{executable_path}'"
            )
            raise ToolExecutionError(f"Unexpected error starting Pwntools process: {e}")

    def interact_remote(
        self,
        host: str,
        port: int,
        interaction_func: Callable[[TubeProtocol], Any],
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Connects to a remote service, executes an interaction function, and closes connection.
        """
        conn: Optional[TubeProtocol] = None
        try:
            conn = self._connect_remote(host, port, timeout)
            result = interaction_func(conn)
            return result
        except ToolExecutionError:
            raise
        except PwnlibException as e:
            logger.error(f"Pwntools remote interaction with {host}:{port} failed: {e}")
            raise ToolExecutionError(f"Pwntools remote interaction failed: {e}")
        except Exception as e:
            logger.exception(
                f"Unexpected error during Pwntools remote interaction with {host}:{port}"
            )
            raise ToolExecutionError(
                f"Unexpected error during Pwntools remote interaction: {e}"
            )
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e_close:
                    logger.warning(
                        f"Error closing pwntools remote connection: {e_close}"
                    )

    def interact_process(
        self,
        executable_path: str,
        interaction_func: Callable[[TubeProtocol], Any],
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Starts a local process, executes an interaction function, and closes connection.
        """
        proc: Optional[TubeProtocol] = None
        try:
            proc = self._start_process(executable_path, timeout)
            result = interaction_func(proc)
            return result
        except ToolExecutionError:
            raise
        except PwnlibException as e:
            logger.error(
                f"Pwntools process interaction with '{executable_path}' failed: {e}"
            )
            raise ToolExecutionError(f"Pwntools process interaction failed: {e}")
        except Exception as e:
            logger.exception(
                f"Unexpected error during Pwntools process interaction with '{executable_path}'"
            )
            raise ToolExecutionError(
                f"Unexpected error during Pwntools process interaction: {e}"
            )
        finally:
            if proc:
                try:
                    proc.close()
                except Exception as e_close:
                    logger.warning(
                        f"Error closing pwntools process connection: {e_close}"
                    )

    def craft_shellcode(self, arch: str, os: str, command: str) -> str:
        """Generates shellcode assembly using pwntools' shellcraft module."""
        try:
            pwn_context.clear()
            pwn_context.arch = arch
            pwn_context.os = os

            if command == "sh":
                return pwn_shellcraft.sh()  # type: ignore
            elif command.startswith("cat"):
                filename = command.split(None, 1)[1]
                return pwn_shellcraft.cat(filename)  # type: ignore
            else:
                raise ToolExecutionError("Unsupported shellcode command.")
        except Exception as e:
            raise ToolExecutionError(f"Shellcode generation failed: {e}")

    def generate_cyclic_pattern(self, length: int, find: Optional[str]) -> str:
        """Generates a cyclic pattern or finds an offset within one."""
        try:
            if find:
                value_to_find = find
                if value_to_find.startswith("0x"):
                    value_to_find = int(value_to_find, 16)
                else:
                    value_to_find = value_to_find.encode("utf-8")
                offset = pwn_cyclic_find(value_to_find, n=4)
                return f"Offset for '{find}' is: {offset}"
            else:
                pattern_bytes = pwn_cyclic(length, n=4)
                return f"Generated pattern: {pattern_bytes.decode('utf-8', errors='ignore')}"  # type: ignore
        except Exception as e:
            raise ToolExecutionError(f"Cyclic pattern operation failed: {e}")

    def inspect_elf(self, file_path: str) -> str:
        """Inspects an ELF binary for security mitigations."""
        try:
            elf = pwn_ELF(file_path)
            results = [
                f"File: {elf.path}",
                f"Arch: {elf.arch}",
                f"Bits: {elf.bits}",
                f"OS: {elf.os}",
                f"RELRO: {elf.relro}",
                f"PIE: {elf.pie}",
                f"NX: {elf.nx}",
                f"Canary: {elf.canary}",
                f"Functions (first 10): {list(elf.functions.keys())[:10]}",
            ]
            return "\n".join(results)
        except FileNotFoundError:
            raise ToolExecutionError(f"ELF file not found: {file_path}")
        except Exception as e:
            raise ToolExecutionError(f"Failed to inspect ELF '{file_path}': {e}")
