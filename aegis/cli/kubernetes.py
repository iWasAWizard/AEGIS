# aegis/cli/kubernetes.py
"""
Kubernetes CLI integration for AEGIS.

Subcommands:
  - pods      : List pods
  - logs      : Show pod logs
  - exec      : Exec inside a pod
  - apply     : Server-side apply manifest (JSON)
  - delete    : Delete an object
  - job       : Create a Job

This is a thin adapter that calls
`aegis.executors.kubernetes_exec.KubernetesExecutor` ToolResult wrappers directly.
No business logic is duplicated here.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
import json
import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_default_category

from aegis.executors.kubernetes_exec import KubernetesExecutor
from aegis.cli._common import print_result


def _make_parser() -> Cmd2ArgumentParser:
    p = Cmd2ArgumentParser(
        prog="kube",
        description="Kubernetes via KubernetesExecutor",
        add_help=True,
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    # pods
    p_pods = sub.add_parser("pods", help="List pods")
    p_pods.add_argument("-n", "--namespace", default="default")
    p_pods.add_argument("--selector", dest="selector")
    p_pods.add_argument("--kubeconfig")
    p_pods.add_argument("--context")
    p_pods.add_argument("--in-cluster", action="store_true")
    p_pods.add_argument("--json", dest="json_out", action="store_true")

    # logs
    p_logs = sub.add_parser("logs", help="Pod logs")
    p_logs.add_argument("name")
    p_logs.add_argument("-n", "--namespace", default="default")
    p_logs.add_argument("--container")
    p_logs.add_argument("--tail", type=int)
    p_logs.add_argument("--kubeconfig")
    p_logs.add_argument("--context")
    p_logs.add_argument("--in-cluster", action="store_true")
    p_logs.add_argument("--json", dest="json_out", action="store_true")

    # exec
    p_exec = sub.add_parser("exec", help="Exec in pod")
    p_exec.add_argument("name")
    p_exec.add_argument("-n", "--namespace", required=True)
    p_exec.add_argument("--container")
    p_exec.add_argument("--tty", action="store_true")
    p_exec.add_argument("--cmd", nargs="+", required=True, help="Command vector")
    p_exec.add_argument("--kubeconfig")
    p_exec.add_argument("--context")
    p_exec.add_argument("--in-cluster", action="store_true")
    p_exec.add_argument("--json", dest="json_out", action="store_true")

    # apply
    p_apply = sub.add_parser("apply", help="Server-side apply manifest (JSON)")
    p_apply.add_argument(
        "manifest_json", help="Manifest as JSON string or @/path/to/file.json"
    )
    p_apply.add_argument("--kubeconfig")
    p_apply.add_argument("--context")
    p_apply.add_argument("--in-cluster", action="store_true")
    p_apply.add_argument("--json", dest="json_out", action="store_true")

    # delete
    p_del = sub.add_parser("delete", help="Delete object")
    p_del.add_argument("kind")
    p_del.add_argument("name")
    p_del.add_argument("-n", "--namespace", default="default")
    p_del.add_argument("--kubeconfig")
    p_del.add_argument("--context")
    p_del.add_argument("--in-cluster", action="store_true")
    p_del.add_argument("--json", dest="json_out", action="store_true")

    # job
    p_job = sub.add_parser("job", help="Create a Job")
    p_job.add_argument("-n", "--namespace", required=True)
    p_job.add_argument("--name", required=True)
    p_job.add_argument("--image", required=True)
    p_job.add_argument("--cmd", nargs="+")
    p_job.add_argument("--env", action="append", help="KEY=VAL (repeatable)")
    p_job.add_argument("--kubeconfig")
    p_job.add_argument("--context")
    p_job.add_argument("--in-cluster", action="store_true")
    p_job.add_argument("--json", dest="json_out", action="store_true")

    return p


@with_default_category("Kubernetes")
class KubernetesCommandSet(cmd2.CommandSet):
    def __init__(self) -> None:
        super().__init__()
        self._parser = _make_parser()

    def _exe(
        self, kubeconfig: Optional[str], context: Optional[str], in_cluster: bool
    ) -> KubernetesExecutor:
        return KubernetesExecutor(
            kubeconfig_path=kubeconfig, context=context, in_cluster=bool(in_cluster)
        )

    @with_argparser(_make_parser())
    def do_kube(self, ns: cmd2.Statement) -> None:
        a = ns

        if a.subcmd == "pods":
            exe = self._exe(a.kubeconfig, a.context, a.in_cluster)
            res = exe.list_pods_result(namespace=a.namespace, label_selector=a.selector)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "logs":
            exe = self._exe(a.kubeconfig, a.context, a.in_cluster)
            res = exe.pod_logs_result(
                name=a.name,
                namespace=a.namespace,
                container=a.container,
                tail_lines=a.tail,
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "exec":
            exe = self._exe(a.kubeconfig, a.context, a.in_cluster)
            res = exe.exec_in_pod_result(
                name=a.name,
                namespace=a.namespace,
                command=a.cmd,
                container=a.container,
                tty=bool(a.tty),
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "apply":
            exe = self._exe(a.kubeconfig, a.context, a.in_cluster)
            manifest_str = a.manifest_json
            if manifest_str.startswith("@"):
                path = manifest_str[1:]
                with open(path, "r", encoding="utf-8") as fh:
                    manifest_str = fh.read()
            try:
                manifest = json.loads(manifest_str)
            except Exception as e:
                self.perror(f"Invalid JSON manifest: {e}")
                return
            res = exe.apply_manifest_result(manifest=manifest)
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "delete":
            exe = self._exe(a.kubeconfig, a.context, a.in_cluster)
            res = exe.delete_object_result(
                kind=a.kind, name=a.name, namespace=a.namespace
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        if a.subcmd == "job":
            exe = self._exe(a.kubeconfig, a.context, a.in_cluster)
            env_map: Dict[str, str] | None = None
            if a.env:
                env_map = {}
                for kv in a.env:
                    if "=" not in kv:
                        self.perror(f"--env expects KEY=VAL, got: {kv}")
                        return
                    k, v = kv.split("=", 1)
                    env_map[k] = v
            res = exe.create_job_result(
                namespace=a.namespace,
                name=a.name,
                image=a.image,
                command=a.cmd,
                env=env_map,
            )
            print_result(self._cmd, res, as_json=bool(a.json_out))
            return

        self.perror(f"Unknown subcommand: {a.subcmd}")


def register(app: cmd2.Cmd) -> None:
    app.add_command_set(KubernetesCommandSet())
