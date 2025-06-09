# aegis/tests/tools/wrappers/test_integration_wrapper.py
"""
Unit tests for the integration wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.integration import (
    schedule_cron_job, ScheduleCronJobInput,
    run_diagnostics_bundle, RunDiagnosticsBundleInput,
    spawn_background_monitor, SpawnBackgroundMonitorInput
)


# --- Fixtures ---

@pytest.fixture
def mock_ssh_executor(monkeypatch):
    """Mocks the SSHExecutor class and its instance methods."""
    mock_instance = MagicMock()
    # Configure the mock to return itself from the constructor
    mock_executor_class = MagicMock(return_value=mock_instance)

    # Patch the SSHExecutor class in the module where it's used
    monkeypatch.setattr("aegis.tools.wrappers.integration.SSHExecutor", mock_executor_class)

    # Also need to mock get_machine to avoid it trying to load real machines
    monkeypatch.setattr("aegis.tools.wrappers.integration.get_machine", MagicMock())

    return mock_instance


# --- Tests ---

def test_schedule_cron_job(mock_ssh_executor):
    """Verify the tool constructs the correct and safe crontab command."""
    cron_entry = "*/5 * * * * /usr/bin/python3 /path/to/script.py"
    input_data = ScheduleCronJobInput(machine_name="test-host", cron_entry=cron_entry)

    schedule_cron_job(input_data)

    expected_cmd = f"(crontab -l 2>/dev/null; echo '{cron_entry}') | crontab -"
    mock_ssh_executor.run.assert_called_once_with(expected_cmd)


def test_run_diagnostics_bundle(mock_ssh_executor):
    """Verify the tool runs the predefined bundle of diagnostic commands."""
    input_data = RunDiagnosticsBundleInput(machine_name="test-host")
    run_diagnostics_bundle(input_data)

    expected_bundle_cmd = (
        "uptime && echo '---' && free -h && echo '---' && df -h && "
        "echo '---' && ps aux | head -n 10 && echo '---' && who && echo '---' && ss -tuln"
    )

    mock_ssh_executor.run.assert_called_once_with(expected_bundle_cmd)


def test_spawn_background_monitor(mock_ssh_executor):
    """Verify the tool correctly wraps a command with nohup for background execution."""
    command_to_run = "/opt/monitor/start.sh --verbose"
    input_data = SpawnBackgroundMonitorInput(machine_name="test-host", command=command_to_run)

    spawn_background_monitor(input_data)

    expected_cmd = f"nohup {command_to_run} > /dev/null 2>&1 &"
    mock_ssh_executor.run.assert_called_once_with(expected_cmd)
