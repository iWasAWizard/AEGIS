# aegis/executors/kubernetes_exec.py
"""
Kubernetes executor with log redaction and ToolResult wrappers.

Requires: kubernetes (python client)
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
import json
import time

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
from aegis.utils.exec_common import (
    now_ms as _common_now_ms,
    map_exception_to_error_type as _common_map_error,
)  # <-- added

logger = setup_logger(__name__)

try:
    from kubernetes import client, config, stream
    from kubernetes.client.exceptions import ApiException

    KUBERNETES_AVAILABLE = True
except Exception:
    KUBERNETES_AVAILABLE = False


class KubernetesExecutor:
    """Thin wrapper over kubernetes client with cautious logging."""

    def __init__(
        self,
        kubeconfig_path: Optional[str] = None,
        context: Optional[str] = None,
        in_cluster: bool = False,
    ):
        """
        :param kubeconfig_path: Path to kubeconfig, if not using in-cluster.
        :param context: Optional context name within kubeconfig.
        :param in_cluster: Use in-cluster config if True.
        """
        if not KUBERNETES_AVAILABLE:
            raise ConfigurationError("The 'kubernetes' Python client is not installed.")
        try:
            if in_cluster:
                config.load_incluster_config()
            else:
                if kubeconfig_path:
                    config.load_kube_config(
                        config_file=kubeconfig_path, context=context
                    )
                else:
                    config.load_kube_config(context=context)
            self.core = client.CoreV1Api()
            self.batch = client.BatchV1Api()
            logger.info("Connected to Kubernetes cluster")
        except Exception as e:
            raise ToolExecutionError(f"Kubernetes config/client error: {e}") from e

    # --- Core ops ---

    def list_pods(
        self, namespace: str = "default", label_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            resp = self.core.list_namespaced_pod(
                namespace=namespace, label_selector=label_selector
            )
            pods: List[Dict[str, Any]] = []
            for p in resp.items:
                status = getattr(p.status, "phase", None)
                pods.append(
                    {
                        "name": p.metadata.name,
                        "ns": p.metadata.namespace,
                        "node": getattr(p.spec, "node_name", None),
                        "status": status,
                        "labels": p.metadata.labels or {},
                    }
                )
            return pods
        except ApiException as e:
            raise ToolExecutionError(f"Kubernetes API error (list pods): {e}") from e

    def pod_logs(
        self,
        name: str,
        namespace: str = "default",
        container: Optional[str] = None,
        tail_lines: Optional[int] = None,
    ) -> str:
        try:
            return self.core.read_namespaced_pod_log(
                name=name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
            )
        except ApiException as e:
            raise ToolExecutionError(f"Kubernetes API error (logs): {e}") from e

    def exec_in_pod(
        self,
        name: str,
        namespace: str,
        command: List[str],
        container: Optional[str] = None,
        tty: bool = False,
    ) -> Tuple[int, str]:
        """
        Exec into a running container; returns (rc, combined_output)
        Note: kubernetes stream returns output text; rc isn't always exposed.
        """
        try:
            out = stream.stream(
                self.core.connect_get_namespaced_pod_exec,
                name,
                namespace,
                command=command,
                container=container,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=tty,
            )
            # Kubernetes exec via stream has no direct rc; assume 0 if we reached here.
            return (0, out)
        except ApiException as e:
            raise ToolExecutionError(f"Kubernetes API error (exec): {e}") from e

    def apply_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Server-side apply via dynamic client is ideal; fallback to minimal create/replace for common kinds.
        """
        try:
            kind = manifest.get("kind", "")
            meta = manifest.get("metadata") or {}
            name = meta.get("name")
            namespace = meta.get("namespace") or "default"

            # Use generic REST call with server-side apply if available
            api = client.ApiClient()
            headers = {"Content-Type": "application/apply-patch+yaml"}
            body = json.dumps(manifest)
            # crude path resolver for a few core kinds
            if kind == "ConfigMap":
                path = f"/api/v1/namespaces/{namespace}/configmaps/{name}"
            elif kind == "Secret":
                path = f"/api/v1/namespaces/{namespace}/secrets/{name}"
            elif kind == "Service":
                path = f"/api/v1/namespaces/{namespace}/services/{name}"
            elif kind == "Pod":
                path = f"/api/v1/namespaces/{namespace}/pods/{name}"
            elif kind == "Job":
                path = f"/apis/batch/v1/namespaces/{namespace}/jobs/{name}"
            else:
                raise ToolExecutionError(f"Unsupported kind for apply_manifest: {kind}")

            resp = api.call_api(
                path,
                "PATCH",
                header_params=headers,
                body=body,
                query_params=[("fieldManager", "aegis"), ("force", "true")],
                response_type="object",
                _preload_content=True,
            )
            # resp is (data, status, headers)
            return {"status": int(resp[1]), "headers": dict(resp[2])}
        except ApiException as e:
            raise ToolExecutionError(f"Kubernetes API error (apply): {e}") from e
        except Exception as e:
            raise ToolExecutionError(f"Kubernetes apply_manifest error: {e}") from e

    def delete_object(self, kind: str, name: str, namespace: str = "default") -> bool:
        try:
            if kind == "Pod":
                self.core.delete_namespaced_pod(name, namespace)
            elif kind == "ConfigMap":
                self.core.delete_namespaced_config_map(name, namespace)
            elif kind == "Secret":
                self.core.delete_namespaced_secret(name, namespace)
            elif kind == "Service":
                self.core.delete_namespaced_service(name, namespace)
            elif kind == "Job":
                self.batch.delete_namespaced_job(name, namespace)
            else:
                raise ToolExecutionError(f"Unsupported kind for delete_object: {kind}")
            return True
        except ApiException as e:
            if getattr(e, "status", None) == 404:
                return False
            raise ToolExecutionError(f"Kubernetes API error (delete): {e}") from e

    def create_job(
        self,
        namespace: str,
        name: str,
        image: str,
        command: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        restart_policy: str = "Never",
    ) -> Dict[str, Any]:
        try:
            spec = client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name=name,
                                image=image,
                                command=command,
                                env=[
                                    client.V1EnvVar(name=k, value=v)
                                    for k, v in (env or {}).items()
                                ],
                            )
                        ],
                        restart_policy=restart_policy,
                    )
                )
            )
            job = client.V1Job(
                api_version="batch/v1",
                kind="Job",
                metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                spec=spec,
            )
            created = self.batch.create_namespaced_job(namespace=namespace, body=job)
            return {"name": created.metadata.name, "uid": created.metadata.uid}
        except ApiException as e:
            raise ToolExecutionError(f"Kubernetes API error (create job): {e}") from e


# === ToolResult wrappers ===


def _now_ms() -> int:
    # Delegate to shared clock for consistency/testability
    return _common_now_ms()


def _errtype(e: Exception) -> str:
    """
    Preserve existing labels while consulting the shared mapper for consistency.
    """
    m = str(e).lower()
    mapped = (_common_map_error(e) or "").lower()
    if "timeout" in m or mapped == "timeout":
        return "Timeout"
    if (
        "forbidden" in m
        or "unauthorized" in m
        or "auth" in m
        or mapped == "permission_denied"
    ):
        return "Auth"
    if "not found" in m or "404" in m or mapped == "not_found":
        return "NotFound"
    if "parse" in m or "json" in m:
        return "Parse"
    return "Runtime"


class KubernetesExecutorToolResultMixin:
    def list_pods_result(
        self, namespace: str = "default", label_selector: Optional[str] = None
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="kubernetes.list_pods",
                args=redact_for_log(
                    {"namespace": namespace, "label_selector": label_selector}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] kubernetes.list_pods",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            pods = self.list_pods(namespace=namespace, label_selector=label_selector)
            return ToolResult.ok_result(
                stdout=json.dumps(pods),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"namespace": namespace},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"namespace": namespace},
            )

    def pod_logs_result(
        self,
        name: str,
        namespace: str = "default",
        container: Optional[str] = None,
        tail_lines: Optional[int] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="kubernetes.pod_logs",
                args=redact_for_log(
                    {"name": name, "namespace": namespace, "container": container}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] kubernetes.pod_logs",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            logs = self.pod_logs(
                name=name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
            )
            return ToolResult.ok_result(
                stdout=logs,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"name": name, "namespace": namespace},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"name": name, "namespace": namespace},
            )

    def exec_in_pod_result(
        self,
        name: str,
        namespace: str,
        command: List[str],
        container: Optional[str] = None,
        tty: bool = False,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="kubernetes.exec",
                args=redact_for_log(
                    {
                        "name": name,
                        "namespace": namespace,
                        "command": command,
                        "container": container,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] kubernetes.exec",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            rc, out = self.exec_in_pod(
                name=name,
                namespace=namespace,
                command=command,
                container=container,
                tty=tty,
            )
            return ToolResult.ok_result(
                stdout=out,
                exit_code=rc,
                latency_ms=_now_ms() - start,
                meta={"name": name, "namespace": namespace},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"name": name, "namespace": namespace},
            )

    def apply_manifest_result(self, manifest: Dict[str, Any]) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            # Redact potential secret data in manifest
            preview = dry_run.preview_payload(
                tool="kubernetes.apply", args=redact_for_log({"manifest": manifest})
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] kubernetes.apply",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            res = self.apply_manifest(manifest=manifest)
            return ToolResult.ok_result(
                stdout=json.dumps(res),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={
                    "kind": manifest.get("kind"),
                    "name": (manifest.get("metadata") or {}).get("name"),
                },
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"kind": manifest.get("kind")},
            )

    def delete_object_result(
        self, kind: str, name: str, namespace: str = "default"
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="kubernetes.delete",
                args=redact_for_log(
                    {"kind": kind, "name": name, "namespace": namespace}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] kubernetes.delete",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            ok = self.delete_object(kind=kind, name=name, namespace=namespace)
            return ToolResult.ok_result(
                stdout=str(ok),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"kind": kind, "name": name},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"kind": kind, "name": name},
            )

    def create_job_result(
        self,
        namespace: str,
        name: str,
        image: str,
        command: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        restart_policy: str = "Never",
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="kubernetes.create_job",
                args=redact_for_log(
                    {"namespace": namespace, "name": name, "image": image, "env": env}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] kubernetes.create_job",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            res = self.create_job(
                namespace=namespace,
                name=name,
                image=image,
                command=command,
                env=env,
                restart_policy=restart_policy,
            )
            return ToolResult.ok_result(
                stdout=json.dumps(res),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"namespace": namespace, "name": name},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"namespace": namespace, "name": name},
            )


KubernetesExecutor.list_pods_result = KubernetesExecutorToolResultMixin.list_pods_result
KubernetesExecutor.pod_logs_result = KubernetesExecutorToolResultMixin.pod_logs_result
KubernetesExecutor.exec_in_pod_result = (
    KubernetesExecutorToolResultMixin.exec_in_pod_result
)
KubernetesExecutor.apply_manifest_result = (
    KubernetesExecutorToolResultMixin.apply_manifest_result
)
KubernetesExecutor.delete_object_result = (
    KubernetesExecutorToolResultMixin.delete_object_result
)
KubernetesExecutor.create_job_result = (
    KubernetesExecutorToolResultMixin.create_job_result
)
