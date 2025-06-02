from aegis.registry import TOOL_REGISTRY
from aegis.tools.primitives.primitive_system import RunLocalCommandInput


def test_run_local_command_success(monkeypatch):
    class MockResult:
        def __init__(self):
            self.stdout = "hello\n"
            self.stderr = ""
            self.returncode = 0

    def mock_run(_):
        return MockResult()

    import subprocess

    monkeypatch.setattr(subprocess, "run", mock_run)

    tool = TOOL_REGISTRY["run_local_command"]
    result = tool.run(RunLocalCommandInput(command="echo hello"))
    assert "hello" in result
