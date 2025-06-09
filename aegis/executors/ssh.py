# aegis/executors/ssh.py
"""
Provides a centralized, robust client for SSH and SCP operations.

This module contains the SSHExecutor class, which is designed to be the single
source of truth for executing commands and transferring files on remote hosts.
It handles connection parameters, authentication, and error handling to ensure
consistent and reliable remote interactions for all tools in the AEGIS framework.
"""

import shlex
import subprocess
from pathlib import Path
from typing import Tuple

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class SSHExecutor:
    """A robust client for executing commands and transferring files on a remote host.

    This class centralizes SSH/SCP logic, including credentials, timeouts, and error handling,
    to be used by various tools across the AEGIS framework.
    """

    def __init__(
        self, host: str, user: str, ssh_key_path: str | None = None, port: int = 22
    ):
        """Initializes the SSHExecutor.

        :param host: The target hostname or IP address.
        :type host: str
        :param user: The username for the SSH connection.
        :type user: str
        :param ssh_key_path: Optional path to the SSH private key.
        :type ssh_key_path: str | None
        :param port: The SSH port on the remote host.
        :type port: int
        :raises ValueError: If host or user are not provided.
        """
        if not host or not user:
            raise ValueError("Host and user must be provided for SSHExecutor.")

        self.host = host
        self.user = user
        self.port = port
        self.ssh_key_path = ssh_key_path
        self.ssh_target = f"{self.user}@{self.host}"

        # Base command options for non-interactive, automated environments.
        self.ssh_opts = [
            "-p",
            str(self.port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]
        self.scp_opts = [
            "-P",
            str(self.port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]
        if self.ssh_key_path:
            self.ssh_opts.extend(["-i", self.ssh_key_path])
            self.scp_opts.extend(["-i", self.ssh_key_path])

    def _run_subprocess(self, command: list[str], timeout: int) -> Tuple[int, str, str]:
        """A private helper to run a subprocess command and capture its output.

        :param command: A list of command arguments for subprocess.run.
        :type command: list[str]
        :param timeout: The timeout for the subprocess in seconds.
        :type timeout: int
        :return: A tuple containing the return code, stdout, and stderr.
        :rtype: Tuple[int, str, str]
        """
        logger.debug(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, check=False
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except FileNotFoundError:
            logger.error(
                f"Command not found: {command[0]}. Is the client (ssh, scp) installed?"
            )
            return -1, "", f"Command not found: {command[0]}"
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout}s: {' '.join(command)}")
            return -1, "", f"Command timed out after {timeout} seconds."
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred while running command: {' '.join(command)}"
            )
            return -1, "", str(e)

    def run(self, command: str, timeout: int = 30) -> str:
        """Executes a shell command on the remote host.

        :param command: The command to execute.
        :type command: str
        :param timeout: The execution timeout in seconds.
        :type timeout: int
        :return: The combined stdout and stderr from the command.
        :rtype: str
        """
        cmd_list = ["ssh", *self.ssh_opts, self.ssh_target, command]
        _, stdout, stderr = self._run_subprocess(cmd_list, timeout=timeout)
        if stderr:
            return f"{stdout}\n[STDERR]\n{stderr}".strip()
        return stdout

    def upload(
        self, local_path: str | Path, remote_path: str | Path, timeout: int = 60
    ) -> str:
        """Uploads a local file to the remote host using SCP.

        :param local_path: The path to the local file.
        :type local_path: str | Path
        :param remote_path: The destination path on the remote host.
        :type remote_path: str | Path
        :param timeout: The transfer timeout in seconds.
        :type timeout: int
        :return: A status message indicating success or failure.
        :rtype: str
        """
        source = str(local_path)
        destination = f"{self.ssh_target}:{remote_path}"
        cmd_list = ["scp", *self.scp_opts, source, destination]
        returncode, stdout, stderr = self._run_subprocess(cmd_list, timeout=timeout)
        if returncode == 0:
            return f"Successfully uploaded {source} to {destination}"
        return f"[ERROR] SCP upload failed: {stderr or stdout}"

    def download(
        self, remote_path: str | Path, local_path: str | Path, timeout: int = 60
    ) -> str:
        """Downloads a remote file to the local machine using SCP.

        :param remote_path: The path to the file on the remote host.
        :type remote_path: str | Path
        :param local_path: The destination path on the local machine.
        :type local_path: str | Path
        :param timeout: The transfer timeout in seconds.
        :type timeout: int
        :return: A status message indicating success or failure.
        :rtype: str
        """
        source = f"{self.ssh_target}:{remote_path}"
        destination = str(local_path)
        cmd_list = ["scp", *self.scp_opts, source, destination]
        returncode, stdout, stderr = self._run_subprocess(cmd_list, timeout=timeout)
        if returncode == 0:
            return f"Successfully downloaded {source} to {destination}"
        return f"[ERROR] SCP download failed: {stderr or stdout}"

    def check_file_exists(self, file_path: str, timeout: int = 20) -> bool:
        """Checks if a file exists on the remote host.

        :param file_path: The absolute path to the file to check.
        :type file_path: str
        :param timeout: The execution timeout in seconds.
        :type timeout: int
        :return: True if the file exists, False otherwise.
        :rtype: bool
        """
        # This command is reliable for checking file existence and prints a specific string on success.
        command = f"test -f {shlex.quote(file_path)} && echo 'AEGIS_FILE_EXISTS'"
        output = self.run(command, timeout=timeout)
        return "AEGIS_FILE_EXISTS" in output
