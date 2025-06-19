# aegis/tests/tools/wrappers/test_scapy_wrapper.py
"""
Unit tests for the scapy wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

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
)

# Mark this entire module to be skipped if scapy is not installed
scapy_all = pytest.importorskip(
    "scapy.all", reason="scapy not installed, skipping scapy tests"
)


# --- Fixtures ---


@pytest.fixture
def mock_scapy_sr1(monkeypatch):
    """Mocks the scapy.all.sr1 function."""
    mock = MagicMock()
    monkeypatch.setattr(scapy_all, "sr1", mock)
    return mock


@pytest.fixture
def mock_scapy_srp(monkeypatch):
    """Mocks the scapy.all.srp function."""
    mock = MagicMock()
    monkeypatch.setattr(scapy_all, "srp", mock)
    return mock


@pytest.fixture
def mock_scapy_sniff(monkeypatch):
    """Mocks the scapy.all.sniff function."""
    mock = MagicMock()
    monkeypatch.setattr(scapy_all, "sniff", mock)
    return mock


@pytest.fixture
def mock_scapy_send(monkeypatch):
    """Mocks the scapy.all.send function."""
    mock = MagicMock()
    monkeypatch.setattr(scapy_all, "send", mock)
    return mock


# --- Tests ---


def test_scapy_ping_host_up(mock_scapy_sr1):
    """Verify ping reports host is up when a reply is received."""
    mock_scapy_sr1.return_value = MagicMock()  # Any non-None object signifies a reply
    result = scapy_ping(ScapyPingInput(target="127.0.0.1"))
    assert "is up" in result


def test_scapy_ping_host_down(mock_scapy_sr1):
    """Verify ping reports host is down when no reply is received."""
    mock_scapy_sr1.return_value = None
    result = scapy_ping(ScapyPingInput(target="127.0.0.1"))
    assert "is down" in result


@pytest.mark.parametrize(
    "tcp_flags, expected_status",
    [
        (0x12, "is open"),  # SYN/ACK
        (0x14, "is closed"),  # RST/ACK
    ],
)
def test_scapy_tcp_scan_open_closed(mock_scapy_sr1, tcp_flags, expected_status):
    """Verify TCP scan correctly identifies open and closed ports."""
    mock_response = MagicMock()
    mock_tcp_layer = MagicMock()
    mock_tcp_layer.flags = tcp_flags
    mock_response.getlayer.return_value = mock_tcp_layer
    mock_response.haslayer.return_value = True
    mock_scapy_sr1.return_value = mock_response

    result = scapy_tcp_scan(ScapyTcpScanInput(target="localhost", port=80))
    assert expected_status in result


def test_scapy_tcp_scan_filtered(mock_scapy_sr1):
    """Verify TCP scan identifies filtered ports when no response is received."""
    mock_scapy_sr1.return_value = None
    result = scapy_tcp_scan(ScapyTcpScanInput(target="localhost", port=80))
    assert "is filtered" in result


def test_scapy_arp_scan(mock_scapy_srp):
    """Verify ARP scan correctly parses and displays discovered hosts."""
    # Mock two answered packets
    answered_packet_1 = (
        MagicMock(),
        MagicMock(psrc="192.168.1.1", hwsrc="00:11:22:aa:bb:cc"),
    )
    answered_packet_2 = (
        MagicMock(),
        MagicMock(psrc="192.168.1.10", hwsrc="00:11:22:dd:ee:ff"),
    )
    mock_scapy_srp.return_value = ([answered_packet_1, answered_packet_2], [])

    result = scapy_arp_scan(ScapyArpScanInput(target_range="192.168.1.0/24"))

    assert "Discovered hosts:" in result
    assert "192.168.1.1" in result
    assert "00:11:22:aa:bb:cc" in result
    assert "192.168.1.10" in result


def test_scapy_sniff(mock_scapy_sniff):
    """Verify sniff calls scapy.sniff and returns a summary."""
    mock_packet_list = MagicMock()
    mock_packet_list.nsummary.return_value = "Packet summary"
    mock_scapy_sniff.return_value = mock_packet_list

    result = scapy_sniff(ScapySniffInput(packet_count=5, filter_bpf="port 80"))

    mock_scapy_sniff.assert_called_once_with(count=5, filter="port 80", timeout=20)
    assert result == "Packet summary"


def test_scapy_craft_and_send(mock_scapy_send):
    """Verify the tool correctly evaluates layer strings and calls send."""
    layers = ["IP(dst='8.8.8.8')", "TCP(dport=443, flags='S')"]
    input_data = ScapyCraftSendInput(layers=layers)
    result = scapy_craft_and_send(input_data)

    mock_scapy_send.assert_called_once()
    # Check the packet object that was sent
    sent_packet = mock_scapy_send.call_args[0][0]
    assert sent_packet.haslayer(scapy_all.IP)
    assert sent_packet[scapy_all.IP].dst == "8.8.8.8"
    assert sent_packet.haslayer(scapy_all.TCP)
    assert sent_packet[scapy_all.TCP].dport == 443
    assert "Successfully sent 1 packet(s)" in result
