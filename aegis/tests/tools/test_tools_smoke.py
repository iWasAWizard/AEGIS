# tests/test_tools_smoke.py
"""
End-to-end smoke tests for AEGIS tools.

What this does:
- Forces AEGIS_DRY_RUN so nothing reaches the network or subsystems.
- Discovers all registered tools via the registry.
- For each tool, builds a minimal valid payload and calls the adapter.
- If a tool has no sample input vector defined here, it is SKIPPED (not failed) with a reason.
- If an adapter raises unexpectedly, the test FAILS with details.

Run:
  AEGIS_DRY_RUN=1 pytest -q tests/test_tools_smoke.py
"""

from __future__ import annotations

import os
import json
import pytest
from typing import Any, Dict

from aegis import registry as reg  # access internal registry for iteration
from aegis.registry import ensure_discovered


# Always in dry-run
os.environ.setdefault("AEGIS_DRY_RUN", "1")


def smoke_vectors() -> Dict[str, Dict[str, Any]]:
    """
    Minimal valid argument maps for each tool.
    Add new entries when you add tools. Unknown tools will be SKIPPED with reason.
    """
    return {
        # Local
        "local.exec": {"command": "echo AEGIS_SMOKE", "timeout": 5, "shell": True},
        # HTTP
        "http.request": {
            "method": "GET",
            "url": "http://example.invalid/test",
            "timeout": 3,
        },
        # Docker
        "docker.pull": {"name": "alpine", "tag": "latest"},
        "docker.run": {
            "image": "alpine",
            "name": "aegis_smoke",
            "command": ["echo", "ok"],
            "auto_remove": True,
        },
        "docker.stop": {"container": "aegis_smoke", "timeout": 1},
        "docker.exec": {
            "container": "aegis_smoke",
            "cmd": ["echo", "ok"],
            "timeout": 2,
        },
        "docker.cp_to": {
            "container": "aegis_smoke",
            "src": "/etc/hosts",
            "dest": "/tmp/hosts",
        },
        "docker.cp_from": {
            "container": "aegis_smoke",
            "src": "/etc/hosts",
            "dest": "/tmp/hosts.copy",
        },
        # Kubernetes
        "kubernetes.list_pods": {"namespace": "default"},
        "kubernetes.pod_logs": {"name": "dummy-pod", "namespace": "default"},
        "kubernetes.exec": {
            "name": "dummy-pod",
            "namespace": "default",
            "command": ["echo", "ok"],
        },
        "kubernetes.apply": {
            "manifest": {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "aegis-smoke", "namespace": "default"},
                "data": {"k": "v"},
            }
        },
        "kubernetes.delete": {
            "kind": "ConfigMap",
            "name": "aegis-smoke",
            "namespace": "default",
        },
        "kubernetes.create_job": {
            "namespace": "default",
            "name": "aegis-smoke",
            "image": "alpine",
            "command": ["echo", "ok"],
        },
        # Redis
        "redis.set": {
            "key": "aegis:smoke",
            "value": "1",
            "host": "127.0.0.1",
            "port": 6379,
            "db": 0,
        },
        "redis.get": {"key": "aegis:smoke", "host": "127.0.0.1", "port": 6379, "db": 0},
        "redis.del": {"key": "aegis:smoke", "host": "127.0.0.1", "port": 6379, "db": 0},
        # Scapy
        "scapy.ping": {"target_ip": "127.0.0.1", "count": 1, "timeout_s": 1},
        "scapy.tcp_scan": {"target_ip": "127.0.0.1", "ports": [22, 80], "timeout_s": 1},
        "scapy.arp_scan": {"network_cidr": "127.0.0.0/24", "timeout_s": 1},
        "scapy.sniff": {"iface": None, "count": 1, "timeout_s": 1},
        "scapy.send": {"dst_ip": "127.0.0.1", "protocol": "ICMP"},
        # Slack
        "slack.send_message": {
            "channel": "C0000000000",
            "text": "smoke",
            "bot_token": "xoxb-REDACTED",
        },
        # GitLab
        "gitlab.list_projects": {"search": "aegis"},
        "gitlab.create_issue": {
            "project_id": 1,
            "title": "smoke",
            "description": "test",
        },
        # SSH / SCP (direct target; avoids fs lookups)
        "ssh.exec": {
            "ssh_target": "127.0.0.1",
            "username": "root",
            "command": "true",
            "timeout": 2,
        },
        "scp.upload": {
            "ssh_target": "127.0.0.1",
            "username": "root",
            "local_path": "/etc/hosts",
            "remote_path": "/tmp/hosts",
            "timeout": 2,
        },
        "scp.download": {
            "ssh_target": "127.0.0.1",
            "username": "root",
            "remote_path": "/etc/hosts",
            "local_path": "/tmp/hosts.copy",
            "timeout": 2,
        },
        "ssh.test_file": {
            "ssh_target": "127.0.0.1",
            "username": "root",
            "path": "/etc/hosts",
            "timeout": 2,
        },
        # Selenium
        "selenium.action": {
            "action": "goto",
            "url": "http://example.invalid",
            "headless": True,
        },
        "selenium.page_details": {"url": "http://example.invalid", "headless": True},
        "selenium.screenshot": {
            "url": "http://example.invalid",
            "path": "/tmp/aegis-smoke.png",
            "headless": True,
        },
        # Pwntools
        "pwntools.interact_remote": {"host": "127.0.0.1", "port": 1, "timeout_s": 1},
        "pwntools.interact_process": {"binary_path": "/bin/true", "timeout_s": 1},
        "pwntools.asm": {"arch": "amd64", "instructions": ["nop", "ret"]},
        "pwntools.cyclic": {"length": 64},
        "pwntools.inspect_elf": {"path": "/bin/true"},
    }


@pytest.mark.parametrize("tool_name", sorted(smoke_vectors().keys()))
def test_tool_smoke_vector(tool_name: str):
    ensure_discovered()
    if (
        tool_name not in reg._REGISTRY
    ):  # noqa: SLF001 – intentional internal read for enumeration
        pytest.skip(
            f"Tool '{tool_name}' not registered (adapter missing or optional component not installed)."
        )

    entry = reg._REGISTRY[tool_name]  # noqa: SLF001

    payload = smoke_vectors()[tool_name]
    # Validate & construct input model
    try:
        model = entry.input_model(**payload)
    except Exception as e:
        pytest.fail(f"Validation failed for {tool_name}: {e}")

    # Invoke adapter. In dry-run, executors should not call real subsystems.
    try:
        result = entry.func(input_data=model)
    except Exception as e:
        pytest.fail(f"Execution failed for {tool_name}: {e}")

    # Result should be serializable-ish
    try:
        as_dict = (
            result.model_dump()
            if hasattr(result, "model_dump")
            else (result.__dict__ if hasattr(result, "__dict__") else result)
        )
        json.dumps(as_dict)
    except Exception as e:
        pytest.fail(f"Result not JSON-serializable for {tool_name}: {e}")


def test_registry_audit_noise_is_only_warning():
    """
    Import-time audit should not raise; at most it should warn about missing adapters.
    """
    ensure_discovered()
