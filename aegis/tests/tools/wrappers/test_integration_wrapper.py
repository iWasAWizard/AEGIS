# aegis/tests/tools/wrappers/test_integration_wrapper.py
"""
Unit tests for the integration wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.integration import (
    schedule_cron_job,
    ScheduleCronJobInput,
    run_diagnostics_bundle,
    RunDiagnosticsBundleInput,
)


@pytest.fixture
def mock_ssh_executor_instance(monkeypatch):
    """Mocks the SSHExecutor instance methods."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = "default mocked command output"

    mock_executor_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aegis.tools.wrappers.integration.SSHExecutor", mock_executor_class
    )
    monkeypatch.setattr("aegis.tools.wrappers.integration.get_machine", MagicMock())
    return mock_instance


# --- Tests ---


def test_schedule_cron_job_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = (
        ""  # crontab command is silent on success
    )
    cron_entry = "0 0 * * * /backup.sh"
    input_data = ScheduleCronJobInput(
        machine_name="backup-server", cron_entry=cron_entry
    )
    result = schedule_cron_job(input_data)

    expected_cmd = f"(crontab -l 2>/dev/null; echo '{cron_entry}') | crontab -"
    mock_ssh_executor_instance.run.assert_called_once_with(expected_cmd)
    assert result == f"Successfully scheduled cron job on backup-server: '{cron_entry}'"


def test_schedule_cron_job_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "crontab command execution failed"
    )
    cron_entry = "0 0 * * * /backup.sh"
    input_data = ScheduleCronJobInput(
        machine_name="backup-server", cron_entry=cron_entry
    )

    with pytest.raises(ToolExecutionError, match="crontab command execution failed"):
        schedule_cron_job(input_data)
    expected_cmd = f"(crontab -l 2>/dev/null; echo '{cron_entry}') | crontab -"
    mock_ssh_executor_instance.run.assert_called_once_with(expected_cmd)


def test_run_diagnostics_bundle_success(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.return_value = "uptime: ...\n---\nfree: ...\n---"
    input_data = RunDiagnosticsBundleInput(machine_name="web-server")
    result = run_diagnostics_bundle(input_data)

    expected_bundle_cmd = (
        "uptime && echo '---' && free -h && echo '---' && df -h && "
        "echo '---' && ps aux | head -n 10 && echo '---' && who && echo '---' && ss -tuln"
    )
    mock_ssh_executor_instance.run.assert_called_once_with(expected_bundle_cmd)
    assert result == "uptime: ...\n---\nfree: ...\n---"


def test_run_diagnostics_bundle_failure(mock_ssh_executor_instance):
    mock_ssh_executor_instance.run.side_effect = ToolExecutionError(
        "Diagnostics bundle failed to execute"
    )
    input_data = RunDiagnosticsBundleInput(machine_name="web-server")

    with pytest.raises(
        ToolExecutionError, match="Diagnostics bundle failed to execute"
    ):
        run_diagnostics_bundle(input_data)
    expected_bundle_cmd = (
        "uptime && echo '---' && free -h && echo '---' && df -h && "
        "echo '---' && ps aux | head -n 10 && echo '---' && who && echo '---' && ss -tuln"
    )
    mock_ssh_executor_instance.run.assert_called_once_with(expected_bundle_cmd)
