# aegis/cli/docker.py
"""
Docker CLI integration for AEGIS.

Subcommands:
  - pull       : Pull an image
  - run        : Run a container
  - stop       : Stop a container
  - exec       : Exec inside a container
  - cp-to      : Copy files/dirs into a container
  - cp-from    : Copy files/dirs out of a container

This is a thin adapter that calls `aegis.executors.docker_exec.DockerExecutor`
ToolResult wrappers directly. No business logic is duplicated here.
"""
from __future__ import annotations

from typing import List, Optional, Dict
import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_default_category

from aegis.executors.docker_exec import DockerExecutor
from aegis.cli._common import print_result


def _vol_list_to_sdk(vols: List[str] | None) -> Dict[str, Dict[str, str]] | None:
    """
    Convert -v host:container[:mode] entries to docker SDK volume dict.
    Example input: ["./data:/mnt/data:ro", "/var/log:/logs"]
    Output: {"./data": {"bind": "/mnt/data", "mode": "ro"}, "/var/log": {"bind": "/logs", "mode": "rw"}}
    """
    if not vols:
        return None
    out: Dict[str, Dict[str, str]] = {}
    for entry in vols:
        parts = entry.split(":")
        if len(parts) < 2:
            continue
        host, container = parts[0], parts[1]
        mode = parts[2] if len(parts) > 2 else "rw"
        out[host] = {"bind": container, "mode": mode}
    return out or None


def _make_parser() -> Cmd2ArgumentParser:
    p = Cmd2ArgumentParser(
        prog="docker",
        description="Docker operations via DockerExecutor",
        add_help=True,
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    # pull
    p_pull = sub.add_parser("pull", help="Pull an image")
    p_pull.add_argument("name", help="Image name, e.g. alpine or repo/name")
    p_pull.add_argument("--tag", default="latest", help="Image tag")
    p_pull.add_argument("--json", dest="json_out", action="store_true")

    # run
    p_run = sub.add_parser("run", help="Run a container")
    p_run.add_argument("image", help="Image")
    p_run.add_argument("--name", help="Container name")
    p_run.add_argument("--command", help="Command (string)")
    p_run.add_argument(
        "--env", dest="env", action="append", help="KEY=VALUE (repeatable)"
    )
    p_run.add_argument(
        "--port",
        dest="ports",
        action="append",
        help="Port publish mapping (free-form; passed through)",
    )
    p_run.add_argument(
        "-v",
        "--volume",
        dest="volumes",
        action="append",
        help="host:container[:mode] (repeatable)",
    )
    p_run.add_argument("-d", "--detach", action="store_true", default=True)
    p_run.add_argument(
        "--rm", dest="auto_remove", action="store_true", help="Auto-remove"
    )
    p_run.add_argument("-w", "--workdir", dest="workdir")
    p_run.add_argument("-u", "--user", dest="user")
    p_run.add_argument("--stdin-open", action="store_true")
    p_run.add_argument("-t", "--tty", action="store_true")
    p_run.add_argument("--json", dest="json_out", action="store_true")

    # stop
    p_stop = sub.add_parser("stop", help="Stop a container")
    p_stop.add_argument("container_id", help="Container ID or name")
    p_stop.add_argument("--timeout", type=int, default=10)
    p_stop.add_argument("--json", dest="json_out", action="store_true")

    # exec
    p_exec = sub.add_parser("exec", help="Exec inside a container")
    p_exec.add_argument("container_id")
    p_exec.add_argument("-w", "--workdir")
    p_exec.add_argument("-u", "--user")
    p_exec.add_argument("-c", "--cmd", required=True, help="Command string")
    p_exec.add_argument("--json", dest="json_out", action="store_true")

    # cp to
    p_cpt = sub.add_parser("cp-to", help="Copy a file/dir into a container")
    p_cpt.add_argument("container_id")
    p_cpt.add_argument("src_path")
    p_cpt.add_argument("dest_path")
    p_cpt.add_argument("--json", dest="json_out", action="store_true")

    # cp from
    p_cpf = sub.add_parser("cp-from", help="Copy a file/dir out of a container")
    p_cpf.add_argument("container_id")
    p_cpf.add_argument("src_path")
    p_cpf.add_argument("dest_dir")
    p_cpf.add_argument("--json", dest="json_out", action="store_true")

    return p


@with_default_category("Docker")
class DockerCommandSet(cmd2.CommandSet):
    def __init__(self) -> None:
        super().__init__()
        self._parser = _make_parser()
        self._executor: DockerExecutor | None = None

    def _exe(self) -> DockerExecutor:
        if self._executor is None:
            self._executor = DockerExecutor()
        return self._executor

    @with_argparser(_make_parser())
    def do_docker(self, ns: cmd2.Statement) -> None:
        args = ns
        exe = self._exe()

        if args.subcmd == "pull":
            res = exe.pull_image_result(name=args.name, tag=args.tag)
            print_result(self._cmd, res, as_json=bool(args.json_out))
            return

        if args.subcmd == "run":
            env = args.env or None
            ports = args.ports or None
            volumes = _vol_list_to_sdk(args.volumes)
            res = exe.run_container_result(
                image=args.image,
                name=args.name,
                command=args.command,
                environment=env,
                ports=ports,
                volumes=volumes,
                detach=bool(args.detach),
                auto_remove=bool(args.auto_remove),
                working_dir=args.workdir,
                user=args.user,
                stdin_open=bool(args.stdin_open),
                tty=bool(args.tty),
            )
            print_result(self._cmd, res, as_json=bool(args.json_out))
            return

        if args.subcmd == "stop":
            res = exe.stop_container_result(
                container_id=args.container_id, timeout=args.timeout
            )
            print_result(self._cmd, res, as_json=bool(args.json_out))
            return

        if args.subcmd == "exec":
            res = exe.exec_in_container_result(
                container_id=args.container_id,
                cmd=args.cmd,  # pass through string
                workdir=args.workdir,
                user=args.user,
            )
            print_result(self._cmd, res, as_json=bool(args.json_out))
            return

        if args.subcmd == "cp-to":
            res = exe.copy_to_container_result(
                args.container_id, args.src_path, args.dest_path
            )
            print_result(self._cmd, res, as_json=bool(args.json_out))
            return

        if args.subcmd == "cp-from":
            res = exe.copy_from_container_result(
                args.container_id, args.src_path, args.dest_dir
            )
            print_result(self._cmd, res, as_json=bool(args.json_out))
            return

        self.perror(f"Unknown subcommand: {args.subcmd}")


def register(app: cmd2.Cmd) -> None:
    app.add_command_set(DockerCommandSet())
