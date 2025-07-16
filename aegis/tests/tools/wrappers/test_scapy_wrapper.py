# aegis/tests/tools/wrappers/test_scapy_wrapper.py
"""
Unit tests for the scapy wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.executors.scapy import ScapyExecutor
from aegis.tools.wrappers.scapy import (
    scapy_ping,
    ScapyPingInput,
    scapy_tcp_scan,
    ScapyTcpScanInput,
    scapy_arp_scan,
    ScapyArpScanInput,
    scapy_sniff,
    ScapySniffInput,
    scapy_craft_and_send,
    ScapyCraftSendInput,
    ScapyLayer,
)

pytest.importorskip("scapy.all", reason="scapy not installed, skipping scapy tests")


@pytest.fixture
def mock_scapy_executor(monkeypatch):
    """Mocks the ScapyExecutor methods."""
    mock = MagicMock()
    mock.ping.return_value = "mocked ping result"
    mock.tcp_scan.return_value = "mocked tcp_scan result"
    mock.arp_scan.return_value = "mocked arp_scan result"
    mock.sniff_packets.return_value = "mocked sniff result"
    mock.craft_and_send_packet.return_value = "mocked craft_and_send result"

    # Patch the class in the module where it's instantiated
    monkeypatch.setattr(
        "aegis.tools.wrappers.scapy.ScapyExecutor", lambda *args, **kwargs: mock
    )
    return mock


def test_scapy_ping_uses_executor(mock_scapy_executor):
    """Verify scapy_ping tool calls the executor's ping method."""
    input_data = ScapyPingInput(target="127.0.0.1", timeout=5)
    result = scapy_ping(input_data)
    mock_scapy_executor.ping.assert_called_once_with("127.0.0.1")
    assert result == "mocked ping result"


def test_scapy_tcp_scan_uses_executor(mock_scapy_executor):
    """Verify scapy_tcp_scan tool calls the executor's tcp_scan method."""
    input_data = ScapyTcpScanInput(target="localhost", port=80, timeout=3)
    result = scapy_tcp_scan(input_data)
    mock_scapy_executor.tcp_scan.assert_called_once_with("localhost", 80)
    assert result == "mocked tcp_scan result"


def test_scapy_arp_scan_uses_executor(mock_scapy_executor):
    """Verify scapy_arp_scan tool calls the executor's arp_scan method."""
    input_data = ScapyArpScanInput(target_range="192.168.1.0/24", timeout=4)
    result = scapy_arp_scan(input_data)
    mock_scapy_executor.arp_scan.assert_called_once_with("192.168.1.0/24")
    assert result == "mocked arp_scan result"


def test_scapy_sniff_uses_executor(mock_scapy_executor):
    """Verify scapy_sniff tool calls the executor's sniff_packets method."""
    input_data = ScapySniffInput(packet_count=15, filter_bpf="tcp", timeout=25)
    result = scapy_sniff(input_data)
    mock_scapy_executor.sniff_packets.assert_called_once_with(15, "tcp", 25)
    assert result == "mocked sniff result"


def test_scapy_craft_and_send_uses_executor(mock_scapy_executor):
    """Verify scapy_craft_and_send tool calls the executor's craft method."""
    layers_data = [ScapyLayer(name="IP", args={"dst": "8.8.8.8"})]
    input_data = ScapyCraftSendInput(layers=layers_data, count=2)
    result = scapy_craft_and_send(input_data)

    expected_layers_dict = [{"name": "IP", "args": {"dst": "8.8.8.8"}}]
    mock_scapy_executor.craft_and_send_packet.assert_called_once_with(
        expected_layers_dict, 2
    )
    assert result == "mocked craft_and_send result"
