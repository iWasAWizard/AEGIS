# tests/executors/test_kubernetes_exec_apply_manifest.py
"""
Validate that apply_manifest uses YAML body when declaring application/apply-patch+yaml.

Test is skipped automatically if the kubernetes client is not installed.
"""
from __future__ import annotations

import json
import types

import pytest

kubernetes = pytest.importorskip("kubernetes")

import aegis.executors.kubernetes_exec as kexec  # noqa: E402


class _FakeApiClient:
    def __init__(self):
        self.calls = []

    def call_api(
        self,
        path,
        method,
        header_params=None,
        body=None,
        query_params=None,
        response_type=None,
        _preload_content=None,
    ):
        self.calls.append(
            {
                "path": path,
                "method": method,
                "headers": dict(header_params or {}),
                "body": body,
                "query": list(query_params or []),
            }
        )
        # emulate (data, status, headers)
        return ({}, 200, {"content-type": "application/json"})


def test_apply_manifest_uses_yaml_when_available(monkeypatch):
    # Monkeypatch ApiClient on the module's imported client object
    fake = _FakeApiClient()
    monkeypatch.setattr(kexec.client, "ApiClient", lambda: fake, raising=True)

    # Build a minimal executor with required attrs (core/batch unused here)
    class _XE:
        pass

    xe = _XE()
    # Attach the bound method from the real class (so 'self' becomes xe)
    xe.apply_manifest = kexec.KubernetesExecutor.apply_manifest.__get__(xe)

    manifest = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "x", "namespace": "default"},
        "data": {"k": "v"},
    }

    out = xe.apply_manifest(manifest)
    assert out["status"] == 200

    # Inspect the captured call
    assert fake.calls, "ApiClient.call_api should have been invoked"
    call = fake.calls[-1]
    assert call["method"] == "PATCH"
    assert call["headers"]["Content-Type"] == "application/apply-patch+yaml"
    # Body should be YAML, not JSON string
    body = call["body"]
    assert isinstance(body, str)
    # A crude but robust check: JSON would start with '{'
    assert not body.strip().startswith("{")
    # And YAML should contain 'kind: ConfigMap' somewhere
    assert "kind: ConfigMap" in body
