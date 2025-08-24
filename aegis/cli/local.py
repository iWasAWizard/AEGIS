# aegis/cli/local.py
"""
Local command execution CLI integration for AEGIS.

Subcommands:
  - run   : Execute a local shell command

This is a thin adapter that calls `aegis.executors.local_exec.LocalExecutor`
ToolResult wrapper directly. No business logic is duplicated here.
"""
from __future__ import annotations

import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_default_category

from aegis.executors.local_exec import LocalExecutor
from aegis.cli._common import print_result


def _make_parser() -> Cmd2ArgumentParser:
    p = Cmd2ArgumentParser(
        prog="local",
        description="Local command execution via LocalExecutor",
        add_help=True,
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    pr = sub.add_parser("run", help="Run a local command")
    pr.add_argument(
        "-c",
        "--cmd",
        required=True,
        help="Command string to execute (quotes recommended for complex shells)",
    )
    pr.add_argument(
        "--shell",
        action="store_true",
        help="Execute through system shell (opt-in; defaults to False)",
    )
    pr.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds (default: 120)",
    )
    pr.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit ToolResult as JSON",
    )

    return p


@with_default_category("Local")
class LocalCommandSet(cmd2.CommandSet):
    def __init__(self) -> None:
        super().__init__()
        self._parser = _make_parser()
        self._executor: LocalExecutor | None = None

    def _exe(self) -> LocalExecutor:
        if self._executor is None:
            self._executor = LocalExecutor()
        return self._executor

    @with_argparser(_make_parser())
    def do_local(self, ns: cmd2.Statement) -> None:
        a = ns

        if a.subcmd == "run":
            exe = self._exe()
            res = exe.run_result(
                a.cmd,
                timeout=a.timeout,
                shell=bool(a.shell),
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        self.perror(f"Unknown subcommand: {a.subcmd}")


def register(app: cmd2.Cmd) -> None:
    app.add_command_set(LocalCommandSet())
