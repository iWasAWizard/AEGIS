# tests/tools/test_docker_wrapper.py
import importlib
import shlex

import pytest

from aegis.registry import reset_registry_for_tests, get_tool
from aegis.schemas.tool_result import ToolResult


@pytest.fixture(autouse=True)
def _fresh_registry(monkeypatch):
    reset_registry_for_tests()
    yield
    reset_registry_for_tests()


def _register_and_patch_docker(monkeypatch):
    mod = importlib.import_module("aegis.tools.wrappers.docker")

    # Patch LocalExecutor.run_result to avoid executing docker
    import aegis.executors.local_exec as lexec

    def fake_run_result(self, command, *, timeout=None, shell=False):
        # Return the command back in meta so we can assert the argv
        return ToolResult.ok_result(
            stdout="ok",
            exit_code=0,
            latency_ms=1,
            meta={"command": command, "shell": shell},
        )

    monkeypatch.setattr(
        lexec.LocalExecutor, "run_result", fake_run_result, raising=True
    )
    return mod


def _split(cmd):
    # mirrors LocalExecutor behavior when shell=False
    return shlex.split(cmd)


def test_docker_ps_builds_expected_cmd(monkeypatch):
    _register_and_patch_docker(monkeypatch)
    entry = get_tool("docker.ps")
    model = entry.input_model(all=True, quiet=True, format="{{json .}}")
    res = entry.func(input_data=model)
    assert res.success is True
    argv = _split(res.meta["command"])
    assert argv[:2] == ["docker", "ps"]
    assert "-a" in argv and "-q" in argv
    assert "--format" in argv and "{{json .}}" in argv


def test_docker_logs_builds_expected_cmd(monkeypatch):
    _register_and_patch_docker(monkeypatch)
    entry = get_tool("docker.logs")
    model = entry.input_model(container="web", tail=100, timestamps=True, follow=False)
    res = entry.func(input_data=model)
    argv = _split(res.meta["command"])
    assert argv[:2] == ["docker", "logs"]
    assert "--tail" in argv and "100" in argv
    assert "-t" in argv
    assert "web" == argv[-1]


def test_docker_exec_builds_expected_cmd(monkeypatch):
    _register_and_patch_docker(monkeypatch)
    entry = get_tool("docker.exec")
    model = entry.input_model(
        container="web", cmd="ls -la /", user="1000:1000", tty=True, env={"FOO": "bar"}
    )
    res = entry.func(input_data=model)
    argv = _split(res.meta["command"])
    # docker exec -t -u 1000:1000 -e FOO=bar web ls -la /
    assert argv[:2] == ["docker", "exec"]
    assert "-t" in argv
    assert "-u" in argv and "1000:1000" in argv
    assert "-e" in argv and "FOO=bar" in argv
    # last elements should include container then command parts
    i = argv.index("web")
    assert argv[i + 1 : i + 3] == ["ls", "-la"]


def test_docker_inspect_builds_expected_cmd(monkeypatch):
    _register_and_patch_docker(monkeypatch)
    entry = get_tool("docker.inspect")
    model = entry.input_model(target="web", format="{{json .State}}")
    res = entry.func(input_data=model)
    argv = _split(res.meta["command"])
    assert argv[:2] == ["docker", "inspect"]
    assert "--format" in argv and "{{json .State}}" in argv
    assert argv[-1] == "web"
