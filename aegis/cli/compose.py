# aegis/cli/compose.py
"""
Docker Compose CLI integration for AEGIS.

Subcommands:
  - up      : Create and start containers
  - down    : Stop and remove containers, networks, images, and volumes
  - ps      : List containers (JSON when supported)
  - logs    : View output from containers (optionally follow)

This is a thin adapter that calls `aegis.executors.compose_exec.ComposeExecutor`
ToolResult wrappers directly. No business logic is duplicated here.
"""
from __future__ import annotations

from typing import List, Optional, Dict
import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_default_category

from aegis.executors.compose_exec import ComposeExecutor
from aegis.cli._common import print_result


def _make_parser() -> Cmd2ArgumentParser:
    p = Cmd2ArgumentParser(
        prog="compose",
        description="Docker Compose operations via ComposeExecutor",
        add_help=True,
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    def add_common(sp: Cmd2ArgumentParser) -> None:
        sp.add_argument(
            "--cwd",
            dest="cwd",
            help="Project working directory (defaults to current working dir)",
        )
        sp.add_argument("-f", "--file", dest="file", help="Compose file path")
        sp.add_argument(
            "-p", "--project-name", dest="project_name", help="Project name"
        )
        sp.add_argument(
            "--profile",
            dest="profiles",
            action="append",
            help="Enable a Compose profile (repeatable)",
        )
        sp.add_argument(
            "--json",
            dest="json_out",
            action="store_true",
            help="Emit ToolResult as JSON",
        )

    # up
    up = sub.add_parser("up", help="Create and start containers")
    add_common(up)
    up.add_argument("services", nargs="*", help="Optional list of services to start")
    up.add_argument(
        "-d",
        "--detach",
        action="store_true",
        default=True,
        help="Run containers in background (default)",
    )
    up.add_argument(
        "--foreground",
        dest="detach",
        action="store_false",
        help="Run in foreground (disables -d)",
    )
    up.add_argument(
        "--build", action="store_true", help="Build images before starting containers"
    )
    up.add_argument(
        "--remove-orphans",
        action="store_true",
        help="Remove containers for services not defined in the Compose file",
    )
    up.add_argument(
        "--pull",
        choices=["always", "missing", "never"],
        help="Pull image policy",
    )
    up.add_argument(
        "--scale",
        action="append",
        dest="scales",
        help="Scale SERVICE=NUM (repeatable)",
    )
    up.add_argument("--timeout", type=int, help="Timeout in seconds")

    # down
    down = sub.add_parser(
        "down", help="Stop and remove containers, networks, images, and volumes"
    )
    add_common(down)
    down.add_argument(
        "-v", "--volumes", action="store_true", help="Remove named volumes"
    )
    down.add_argument(
        "--remove-orphans",
        action="store_true",
        help="Remove containers for services not defined in the Compose file",
    )
    down.add_argument("--timeout", type=int, help="Timeout in seconds")

    # ps
    ps = sub.add_parser("ps", help="List containers (JSON when supported)")
    add_common(ps)
    ps.add_argument("--timeout", type=int, help="Timeout in seconds")

    # logs
    logs = sub.add_parser("logs", help="View output from containers")
    add_common(logs)
    logs.add_argument("services", nargs="*", help="Services to show logs for")
    logs.add_argument(
        "--tail",
        type=int,
        help="Number of lines to show from the end of the logs for each container",
    )
    logs.add_argument("-t", "--timestamps", action="store_true", help="Show timestamps")
    logs.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    logs.add_argument(
        "--timeout",
        type=int,
        help="Timeout in seconds (ignored when following unless provided)",
    )

    return p


def _parse_scales(values: Optional[List[str]]) -> Dict[str, int]:
    scales: Dict[str, int] = {}
    if not values:
        return scales
    for item in values:
        if "=" not in item:
            raise ValueError(f"--scale expects SERVICE=NUM, got: {item}")
        svc, num = item.split("=", 1)
        svc = svc.strip()
        try:
            n = int(num.strip())
        except ValueError:
            raise ValueError(f"--scale expects integer count, got: {num}")
        if not svc:
            raise ValueError(f"--scale missing service name in: {item}")
        scales[svc] = n
    return scales


@with_default_category("Compose")
class ComposeCommandSet(cmd2.CommandSet):
    def __init__(self) -> None:
        super().__init__()
        self._parser = _make_parser()

    def _exe(self, cwd: Optional[str]) -> ComposeExecutor:
        return ComposeExecutor(project_dir=cwd)

    @with_argparser(_make_parser())
    def do_compose(self, ns: cmd2.Statement) -> None:
        a = ns

        if a.subcmd == "up":
            try:
                scales = _parse_scales(a.scales)
            except ValueError as e:
                self.perror(str(e))
                return
            exe = self._exe(a.cwd)
            res = exe.up_result(
                project_dir=a.cwd,
                file=a.file,
                profiles=a.profiles,
                services=a.services,
                build=bool(a.build),
                detach=bool(a.detach),
                remove_orphans=bool(a.remove_orphans),
                pull=a.pull,
                project_name=a.project_name,
                scales=scales or None,
                timeout=a.timeout,
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "down":
            exe = self._exe(a.cwd)
            res = exe.down_result(
                project_dir=a.cwd,
                file=a.file,
                volumes=bool(a.volumes),
                remove_orphans=bool(a.remove_orphans),
                project_name=a.project_name,
                timeout=a.timeout,
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "ps":
            exe = self._exe(a.cwd)
            res = exe.ps_result(
                project_dir=a.cwd,
                file=a.file,
                project_name=a.project_name,
                timeout=a.timeout,
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "logs":
            exe = self._exe(a.cwd)
            res = exe.logs_result(
                project_dir=a.cwd,
                services=a.services,
                file=a.file,
                project_name=a.project_name,
                tail=a.tail,
                timestamps=bool(a.timestamps),
                follow=bool(a.follow),
                timeout=a.timeout,
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        self.perror(f"Unknown subcommand: {a.subcmd}")


def register(app: cmd2.Cmd) -> None:
    app.add_command_set(ComposeCommandSet())
