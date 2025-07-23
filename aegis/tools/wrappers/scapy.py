# aegis/tools/wrappers/scapy_exec.py
"""
Wrapper tools for leveraging the 'scapy' library for network packet
crafting, sending, and analysis.

These tools provide a structured interface to scapy's powerful networking
capabilities, allowing the agent to perform low-level network tasks like
pinging, port scanning, and custom packet generation.
"""

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.scapy_exec import ScapyExecutor, SCAPY_AVAILABLE
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# --- Input Models ---


class ScapyPingInput(BaseModel):
    """Input model for sending a single ICMP ping packet."""

    target: str = Field(
        ..., description="The destination IP address or hostname to ping."
    )
    timeout: int = Field(2, description="The time in seconds to wait for a reply.")


class ScapyTcpScanInput(BaseModel):
    """Input model for scanning a single TCP port."""

    target: str = Field(..., description="The destination IP address or hostname.")
    port: int = Field(..., gt=0, lt=65536, description="The TCP port to scan.")
    timeout: int = Field(2, description="The time in seconds to wait for a reply.")


class ScapyLayer(BaseModel):
    """Defines a single, safe layer for packet crafting."""

    name: str = Field(
        ..., description="The name of the Scapy layer (e.g., 'IP', 'TCP')."
    )
    args: Dict[str, Any] = Field(
        default_factory=dict, description="A dictionary of arguments for the layer."
    )


class ScapyCraftSendInput(BaseModel):
    """A safe input model for crafting and sending a custom packet."""

    layers: List[ScapyLayer] = Field(
        ..., description="A list of Scapy layers to construct the packet."
    )
    count: int = Field(1, description="The number of packets to send.")


class ScapyArpScanInput(BaseModel):
    """Input model for performing an ARP scan on a network range."""

    target_range: str = Field(
        ...,
        description="The target network range in CIDR notation (e.g., '192.168.1.0/24').",
    )
    timeout: int = Field(2, description="The timeout in seconds for the scan.")


class ScapySniffInput(BaseModel):
    """Input model for sniffing network packets."""

    packet_count: int = Field(10, description="The number of packets to capture.")
    filter_bpf: Optional[str] = Field(
        None, description="Optional BPF filter string (e.g., 'tcp port 80')."
    )
    timeout: int = Field(
        20, description="The maximum time in seconds to wait for the packets."
    )


# --- Tools ---


@register_tool(
    name="scapy_ping",
    input_model=ScapyPingInput,
    description="Sends a single ICMP (ping) packet to a target to check for reachability.",
    tags=["scapy", "network", "scan", "icmp"],
    category="network",
    safe_mode=False,
)
def scapy_ping(input_data: ScapyPingInput) -> str:
    """Uses scapy to send an ICMP echo request and determines if the host is up."""
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")
    executor = ScapyExecutor(default_timeout=input_data.timeout)
    return executor.ping(input_data.target)


@register_tool(
    name="scapy_tcp_scan",
    input_model=ScapyTcpScanInput,
    description="Performs a stealthy TCP SYN scan on a single port to check if it's open, closed, or filtered.",
    tags=["scapy", "network", "scan", "tcp"],
    category="network",
    safe_mode=False,
)
def scapy_tcp_scan(input_data: ScapyTcpScanInput) -> str:
    """Sends a single TCP SYN packet and analyzes the reply to determine port state."""
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")
    executor = ScapyExecutor(default_timeout=input_data.timeout)
    return executor.tcp_scan(input_data.target, input_data.port)


@register_tool(
    name="scapy_craft_and_send",
    input_model=ScapyCraftSendInput,
    description="Dynamically crafts and sends a custom packet defined by a list of layers.",
    tags=["scapy", "network", "crafting", "packet"],
    category="network",
    safe_mode=False,
)
def scapy_craft_and_send(input_data: ScapyCraftSendInput) -> str:
    """Constructs a packet from a list of structured layer objects and sends it."""
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")
    executor = ScapyExecutor()
    layers_as_dicts = [layer.model_dump() for layer in input_data.layers]
    return executor.craft_and_send_packet(layers_as_dicts, input_data.count)


@register_tool(
    name="scapy_arp_scan",
    input_model=ScapyArpScanInput,
    description="Performs an ARP scan to discover live hosts on a local network range.",
    tags=["scapy", "network", "discovery", "arp", "scan"],
    category="network",
    safe_mode=False,
)
def scapy_arp_scan(input_data: ScapyArpScanInput) -> str:
    """Uses scapy to send ARP requests to a network range and reports discovered hosts."""
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")
    executor = ScapyExecutor(default_timeout=input_data.timeout)
    return executor.arp_scan(input_data.target_range)


@register_tool(
    name="scapy_sniff",
    input_model=ScapySniffInput,
    description="Captures network packets on the local interface, with an optional filter.",
    tags=["scapy", "network", "sniffing", "pcap"],
    category="network",
    safe_mode=False,
)
def scapy_sniff(input_data: ScapySniffInput) -> str:
    """Uses scapy to sniff network traffic and returns a summary of captured packets."""
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")
    executor = ScapyExecutor()
    return executor.sniff_packets(
        input_data.packet_count, input_data.filter_bpf, input_data.timeout
    )
