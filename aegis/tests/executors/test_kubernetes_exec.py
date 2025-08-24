# tests/executors/test_kubernetes_exec.py
import json
import pytest

from aegis.executors.kubernetes_exec import KubernetesExecutor


def _mk_executor(monkeypatch):
    """
    Create a KubernetesExecutor without touching real kubernetes libs.
    We monkeypatch __init__ to avoid imports and just attach the attributes we need.
    """

    def fake_init(self, kubeconfig_path=None, context=None, in_cluster=False):
        self.core = object()
        self.batch = object()
        self.default_timeout = 5

    monkeypatch.setattr(KubernetesExecutor, "__init__", fake_init, raising=True)
    return KubernetesExecutor()  # type: ignore[call-arg]


def test_list_pods_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    pods = [
        {
            "name": "p1",
            "ns": "default",
            "node": "n1",
            "status": "Running",
            "labels": {"app": "x"},
        }
    ]
    monkeypatch.setattr(exe, "list_pods", lambda **kwargs: pods, raising=True)

    res = exe.list_pods_result(namespace="default")
    assert getattr(res, "ok", False) is True
    assert json.loads(res.stdout) == pods
    assert res.exit_code == 0
    assert res.meta.get("namespace") == "default"


def test_pod_logs_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(
        exe, "pod_logs", lambda **kwargs: "logline1\nlogline2\n", raising=True
    )

    res = exe.pod_logs_result(name="p1", namespace="ns1")
    assert res.ok is True
    assert "logline1" in (res.stdout or "")
    assert res.exit_code == 0
    assert res.meta.get("name") == "p1"


def test_exec_in_pod_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "exec_in_pod", lambda **kwargs: (0, "done"), raising=True)

    res = exe.exec_in_pod_result(name="p1", namespace="ns1", command=["/bin/true"])
    assert res.ok is True
    assert res.exit_code == 0
    assert res.stdout.strip() == "done"


def test_delete_object_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    monkeypatch.setattr(exe, "delete_object", lambda **kwargs: True, raising=True)

    res = exe.delete_object_result(kind="Pod", name="p1", namespace="ns1")
    assert res.ok is True
    assert res.stdout == "True"
    assert res.exit_code == 0


def test_create_job_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    job_info = {"name": "job-1", "uid": "abc123"}
    monkeypatch.setattr(
        exe,
        "create_job",
        lambda **kwargs: job_info,
        raising=True,
    )

    res = exe.create_job_result(namespace="ns1", name="job-1", image="busybox")
    assert res.ok is True
    assert json.loads(res.stdout) == job_info
    assert res.exit_code == 0
    assert res.meta.get("namespace") == "ns1"


def test_list_pods_result_error_mapping_timeout(monkeypatch):
    exe = _mk_executor(monkeypatch)

    class Timeouty(Exception):
        def __str__(self):
            return "read timeout while contacting apiserver"

    def boom(**kwargs):
        raise Timeouty()

    monkeypatch.setattr(exe, "list_pods", boom, raising=True)

    res = exe.list_pods_result(namespace="ns1")
    assert res.ok is False
    # Ensure our shared mapper / local labels surface "Timeout"
    assert res.error_type == "Timeout"
    assert "timeout" in (res.stderr or "").lower()
