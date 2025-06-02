from aegis.tools.wrappers.wrapper_system import check_remote_processes
from aegis.tools.wrappers.wrapper_system import CheckRemoteProcessesInput


def test_check_remote_processes(monkeypatch):
    class MockResponse:
        def __init__(self, stdout, stderr, returncode=0):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    def mock_run(_):
        return MockResponse("PID USER COMMAND\n1234 root python", "")

    import subprocess

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = check_remote_processes(
        CheckRemoteProcessesInput(
            host="192.168.1.100", ssh_key_path="/mnt/user/privkey.whatever"
        )
    )

    assert "PID" in result and "COMMAND" in result
