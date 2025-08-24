# aegis/cli/ssh.py
"""
SSH/SCP CLI integration for AEGIS.

Subcommands:
  - run        : Run a remote command over SSH
  - upload     : Copy a local file to the remote host via SCP
  - download   : Copy a remote file to the local machine via SCP
  - test-file  : Check if a remote file exists

This is a thin adapter that calls `aegis.executors.ssh_exec.SSHExecutor`
ToolResult wrappers directly. No business logic is duplicated here.
"""
from __future__ import annotations

from typing import Optional
import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_default_category

from aegis.executors.ssh_exec import SSHExecutor
from aegis.cli._common import print_result


def _make_parser() -> Cmd2ArgumentParser:
    p = Cmd2ArgumentParser(
        prog="ssh",
        description="SSH/SCP operations via SSHExecutor",
        add_help=True,
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    # run
    pr = sub.add_parser("run", help="Run a command over SSH")
    pr.add_argument("--host", required=True, help="Target hostname or IP")
    pr.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    pr.add_argument("--user", default="root", help="Username (default: root)")
    pr.add_argument("--key-path", dest="key_path", help="Path to private key")
    pr.add_argument("--password", help="Password (discouraged; prefer keys)")
    pr.add_argument("--timeout", type=int, default=120, help="Timeout seconds")
    pr.add_argument("-c", "--cmd", required=True, help="Command to execute")
    pr.add_argument(
        "--json", dest="json_out", action="store_true", help="Emit ToolResult as JSON"
    )

    # upload
    pu = sub.add_parser("upload", help="Upload a file via SCP")
    pu.add_argument("--host", required=True)
    pu.add_argument("--port", type=int, default=22)
    pu.add_argument("--user", default="root")
    pu.add_argument("--key-path", dest="key_path")
    pu.add_argument("--password")
    pu.add_argument("--timeout", type=int, default=120)
    pu.add_argument("local_path")
    pu.add_argument("remote_path")
    pu.add_argument("--json", dest="json_out", action="store_true")

    # download
    pd = sub.add_parser("download", help="Download a file via SCP")
    pd.add_argument("--host", required=True)
    pd.add_argument("--port", type=int, default=22)
    pd.add_argument("--user", default="root")
    pd.add_argument("--key-path", dest="key_path")
    pd.add_argument("--password")
    pd.add_argument("--timeout", type=int, default=120)
    pd.add_argument("remote_path")
    pd.add_argument("local_path")
    pd.add_argument("--json", dest="json_out", action="store_true")

    # test-file
    pt = sub.add_parser("test-file", help="Check if a remote file exists")
    pt.add_argument("--host", required=True)
    pt.add_argument("--port", type=int, default=22)
    pt.add_argument("--user", default="root")
    pt.add_argument("--key-path", dest="key_path")
    pt.add_argument("--password")
    pt.add_argument("--timeout", type=int, default=120)
    pt.add_argument("path")
    pt.add_argument("--json", dest="json_out", action="store_true")

    return p


@with_default_category("SSH")
class SSHCommandSet(cmd2.CommandSet):
    def __init__(self) -> None:
        super().__init__()
        self._parser = _make_parser()

    def _exe(
        self,
        host: str,
        port: int,
        user: str,
        key: Optional[str],
        password: Optional[str],
        timeout: int,
    ) -> SSHExecutor:
        # Construct using direct ssh_target path to avoid manifest requirements
        return SSHExecutor(
            ssh_target=host,
            username=user,
            port=port,
            private_key_path=key,
            password=password,
            timeout=timeout,
        )

    @with_argparser(_make_parser())
    def do_ssh(self, ns: cmd2.Statement) -> None:
        a = ns

        if a.subcmd == "run":
            exe = self._exe(a.host, a.port, a.user, a.key_path, a.password, a.timeout)
            res = exe.run_result(a.cmd, timeout=a.timeout)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "upload":
            exe = self._exe(a.host, a.port, a.user, a.key_path, a.password, a.timeout)
            res = exe.upload_result(a.local_path, a.remote_path, timeout=a.timeout)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "download":
            exe = self._exe(a.host, a.port, a.user, a.key_path, a.password, a.timeout)
            res = exe.download_result(a.remote_path, a.local_path, timeout=a.timeout)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "test-file":
            exe = self._exe(a.host, a.port, a.user, a.key_path, a.password, a.timeout)
            res = exe.check_file_exists_result(a.path, timeout=a.timeout)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        self.perror(f"Unknown subcommand: {a.subcmd}")


def register(app: cmd2.Cmd) -> None:
    app.add_command_set(SSHCommandSet())
