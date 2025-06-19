# aegis/tests/tools/primitives/test_process_primitives.py
"""
Unit tests for the process and resource primitive tools.
"""
from collections import namedtuple
from unittest.mock import MagicMock

import psutil
import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.primitives.process import (
    list_processes,
    ListProcessesInput,
    get_disk_usage,
    GetDiskUsageInput,
)


@pytest.fixture
def mock_psutil(monkeypatch):
    """Mocks the entire psutil library."""
    mock = MagicMock()
    monkeypatch.setattr("aegis.tools.primitives.process.psutil", mock)
    return mock


def test_list_processes(mock_psutil):
    """Verify list_processes correctly formats data from psutil.process_iter."""
    # Create mock process objects
    p1_mock = MagicMock()
    p1_mock.pid = 101
    p1_mock.name.return_value = "process1"
    p1_mock.username.return_value = "user1"

    p2_mock = MagicMock()
    p2_mock.pid = 202
    p2_mock.name.return_value = "process2"
    p2_mock.username.return_value = "root"

    mock_psutil.process_iter.return_value = [p1_mock, p2_mock]

    result = list_processes(ListProcessesInput())

    assert "PID: 101" in result
    assert "User: user1" in result
    assert "Name: process1" in result
    assert "PID: 202" in result
    assert "User: root" in result
    assert "Name: process2" in result


def test_list_processes_failure(mock_psutil):
    """Verify list_processes raises ToolExecutionError on psutil failure."""
    mock_psutil.process_iter.side_effect = psutil.Error("psutil failed")
    with pytest.raises(ToolExecutionError, match="Could not list processes"):
        list_processes(ListProcessesInput())


def test_get_disk_usage(mock_psutil):
    """Verify get_disk_usage correctly formats data from psutil.disk_usage."""
    # psutil.disk_usage returns a named tuple, so we simulate that
    sdiskusage = namedtuple("sdiskusage", ["total", "used", "free", "percent"])
    mock_usage = sdiskusage(
        total=100 * 1024**3,  # 100 GB
        used=25 * 1024**3,  # 25 GB
        free=75 * 1024**3,  # 75 GB
        percent=25.0,
    )
    mock_psutil.disk_usage.return_value = mock_usage

    result = get_disk_usage(GetDiskUsageInput(path="/"))

    assert "Total: 100.00 GB" in result
    assert "Used:  25.00 GB (25.0%)" in result
    assert "Free:  75.00 GB" in result


def test_get_disk_usage_not_found(mock_psutil):
    """Verify get_disk_usage handles FileNotFoundError cleanly."""
    mock_psutil.disk_usage.side_effect = FileNotFoundError("Path not found")
    result = get_disk_usage(GetDiskUsageInput(path="/nonexistent"))
    assert "[ERROR] Path not found" in result
