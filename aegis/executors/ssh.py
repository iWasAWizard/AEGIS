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

from aegis.schemas.machine import MachineManifest
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class SSHExecutor:
    """A robust client for executing commands and transferring files on a remote host."""

    def __init__(self, machine: MachineManifest):
        """Initializes the SSHExecutor from a resolved machine configuration.

        :param machine: A validated MachineManifest object containing connection details.
        :type machine: MachineManifest
        :raises ValueError: If the machine configuration is missing IP or username.
        """
        if not all([machine.ip, machine.username]):
            raise ValueError("Machine config must have ip and username.")

        self.machine = machine
        self.ssh_target = f"{self.machine.username}@{self.machine.ip}"

        self.ssh_opts = [
            "-p",
            str(self.machine.ssh_port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]
        self.scp_opts = [
            "-P",
            str(self.machine.ssh_port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]

    @staticmethod
    def _run_subprocess(command: list[str], timeout: int) -> Tuple[int, str, str]:
        """A private helper to run a subprocess command and capture its output.

        :param command: A list of strings representing the command and its arguments.
        :type command: list[str]
        :param timeout: The timeout in seconds for the command.
        :type timeout: int
        :return: A tuple of (returncode, stdout, stderr).
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
        """Executes a shell command on the remote host via SSH.

        :param command: The shell command to execute.
        :type command: str
        :param timeout: The timeout in seconds for the command.
        :type timeout: int
        :return: The combined stdout and stderr from the remote command.
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

        :param local_path: The path to the local file to upload.
        :type local_path: str | Path
        :param remote_path: The destination path on the remote host.
        :type remote_path: str | Path
        :param timeout: The timeout in seconds for the transfer.
        :type timeout: int
        :return: A success or error message.
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

        :param remote_path: The path to the remote file to download.
        :type remote_path: str | Path
        :param local_path: The destination path on the local machine.
        :type local_path: str | Path
        :param timeout: The timeout in seconds for the transfer.
        :type timeout: int
        :return: A success or error message.
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
        """Checks if a file exists on the remote host using a reliable test command.

        :param file_path: The absolute path to the file on the remote host.
        :type file_path: str
        :param timeout: The timeout in seconds for the check.
        :type timeout: int
        :return: True if the file exists, False otherwise.
        :rtype: bool
        """
        command = f"test -f {shlex.quote(file_path)} && echo 'AEGIS_FILE_EXISTS'"
        output = self.run(command, timeout=timeout)
        return "AEGIS_FILE_EXISTS" in output
