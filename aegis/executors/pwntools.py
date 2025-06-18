# aegis/executors/pwntools.py
"""
Provides a client for executing pwntools-based interactions.
"""
from typing import Callable, Any, Optional

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# Import pwntools conditionally for the executor
try:
    from pwn import remote as pwn_remote, process as pwn_process  # type: ignore
    from pwnlib.tubes.tube import tube  # type: ignore
    from pwnlib.exception import PwnlibException  # type: ignore

    PWNTOOLS_AVAILABLE_FOR_EXECUTOR = True
except ImportError:
    PWNTOOLS_AVAILABLE_FOR_EXECUTOR = False

    # Define dummy types if pwntools is not available, for type hinting
    class tube:
        pass  # type: ignore

    class PwnlibException(Exception):
        pass  # type: ignore


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
            # This check is mostly for environments where executor might be instantiated
            # even if the tool itself checks.
            raise ToolExecutionError(
                "Pwntools library is not installed. Cannot use PwntoolsExecutor."
            )
        self.default_timeout = default_timeout

    def _connect_remote(self, host: str, port: int, timeout: Optional[int]) -> tube:
        """Establishes a pwntools remote connection."""
        effective_timeout = timeout if timeout is not None else self.default_timeout
        logger.debug(
            f"PwntoolsExecutor: Connecting to remote {host}:{port} with timeout {effective_timeout}s"
        )
        try:
            conn = pwn_remote(host, port, timeout=effective_timeout)
            return conn
        except PwnlibException as e:  # type: ignore
            logger.error(f"Pwntools remote connection to {host}:{port} failed: {e}")
            raise ToolExecutionError(
                f"Pwntools remote connection to {host}:{port} failed: {e}"
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error during pwntools remote connection to {host}:{port}"
            )
            raise ToolExecutionError(f"Unexpected error connecting with pwntools: {e}")

    def _start_process(self, executable_path: str, timeout: Optional[int]) -> tube:
        """Starts a local process using pwntools."""
        # Note: pwntools.process doesn't directly take a timeout for the initial start,
        # but operations on the tube can timeout.
        effective_timeout = timeout if timeout is not None else self.default_timeout
        logger.debug(
            f"PwntoolsExecutor: Starting process {executable_path} (ops timeout {effective_timeout}s)"
        )
        try:
            proc = pwn_process(executable_path)  # type: ignore
            # We can set a default timeout on the tube for subsequent operations
            proc.timeout = effective_timeout  # type: ignore
            return proc
        except FileNotFoundError:
            logger.error(
                f"Executable not found for Pwntools process: '{executable_path}'"
            )
            raise ToolExecutionError(
                f"Pwntools process: Executable not found at '{executable_path}'"
            )
        except PwnlibException as e:  # type: ignore
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
        interaction_func: Callable[[tube], Any],
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Connects to a remote service, executes an interaction function, and closes connection.

        :param host: Target host.
        :param port: Target port.
        :param interaction_func: Callable that takes a pwntools tube and performs actions.
        :param timeout: Optional timeout for connection and operations.
        :return: Result of the interaction_func.
        :raises ToolExecutionError: If connection or interaction fails.
        """
        conn = None
        try:
            conn = self._connect_remote(host, port, timeout)
            result = interaction_func(conn)
            return result
        # ToolExecutionError from _connect_remote or interaction_func will propagate
        except ToolExecutionError:
            raise
        except PwnlibException as e:  # type: ignore # Catch specific pwntools errors during interaction
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
        interaction_func: Callable[[tube], Any],
        timeout: Optional[int] = None,  # Timeout for operations on the tube
    ) -> Any:
        """
        Starts a local process, executes an interaction function, and closes connection.

        :param executable_path: Path to the local executable.
        :param interaction_func: Callable that takes a pwntools tube and performs actions.
        :param timeout: Optional timeout for operations on the tube.
        :return: Result of the interaction_func.
        :raises ToolExecutionError: If process start or interaction fails.
        """
        proc = None
        try:
            proc = self._start_process(executable_path, timeout)
            result = interaction_func(proc)
            return result
        except ToolExecutionError:  # Re-raise from _start_process or interaction_func
            raise
        except PwnlibException as e:  # type: ignore # Catch specific pwntools errors during interaction
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
