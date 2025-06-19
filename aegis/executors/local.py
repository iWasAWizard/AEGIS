# aegis/executors/local.py
"""
Provides a client for executing local shell commands.
"""
import shlex
import subprocess
from typing import Tuple, Optional

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class LocalExecutor:
    """A client for executing local shell commands consistently."""

    def __init__(self, default_timeout: int = 60):
        """
        Initializes the LocalExecutor.

        :param default_timeout: Default timeout in seconds for commands.
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
        :raises ToolExecutionError: For FileNotFoundError (if shell=False and cmd not found) or TimeoutExpired.
        """
        cmd_to_log = command_str
        cmd_arg: str | list[str]
        if not shell:
            cmd_arg = shlex.split(command_str)
            cmd_to_log = " ".join(shlex.quote(c) for c in cmd_arg)
        else:
            cmd_arg = command_str

        logger.debug(f"Executing local command (shell={shell}): {cmd_to_log}")
        try:
            result = subprocess.run(
                cmd_arg,  # type: ignore
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                encoding="utf-8",
                errors="surrogateescape",
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except FileNotFoundError as e:
            logger.error(
                f"Local command executable not found "
                f"(shell={shell}): {command_str.split()[0] if not shell else command_str}. Error: {e}"
            )
            raise ToolExecutionError(
                f"Local command executable not found: {command_str.split()[0] if not shell else command_str}"
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Local command timed out after {timeout}s: {cmd_to_log}")
            raise ToolExecutionError(
                f"Local command timed out after {timeout}s: {cmd_to_log}"
            )
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred while running local command: {cmd_to_log}"
            )
            raise ToolExecutionError(
                f"Unexpected error during local command execution for '{cmd_to_log}': {e}"
            )

    def run(
        self, command: str, shell: bool = True, timeout: Optional[int] = None
    ) -> str:
        """
        Executes a shell command on the local machine.

        :param command: The shell command to execute.
        :type command: str
        :param shell: Whether to use the shell for execution.
                      Security warning: if command comes from untrusted input, shell=True is a risk.
        :type shell: bool
        :param timeout: Optional timeout in seconds for this specific command.
                        If None, uses default_timeout.
        :type timeout: Optional[int]
        :return: The combined stdout and stderr from the command if successful.
        :rtype: str
        :raises ToolExecutionError: If the command fails (non-zero exit code) or other execution error.
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout

        returncode, stdout, stderr = self._run_subprocess(
            command, shell, effective_timeout
        )

        combined_output = stdout
        if stderr:
            combined_output = f"{stdout}\n[STDERR]\n{stderr}".strip()

        if returncode != 0:
            logger.error(
                f"Local command '{command}' failed with RC {returncode}. Output:\n{combined_output}"
            )
            raise ToolExecutionError(
                f"Local command failed with exit code {returncode}. Output: {combined_output}"
            )

        return combined_output
