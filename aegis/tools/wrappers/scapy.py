# aegis/tools/wrappers/scapy.py
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
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

try:
    import scapy.all as scapy
    from scapy.all import srp, sr1, IP, ICMP, TCP, ARP, Ether, send, sniff

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

logger = setup_logger(__name__)


# --- Input Models ---


class ScapyPingInput(BaseModel):
    """Input model for sending a single ICMP ping packet.

    :ivar target: The destination IP address or hostname to ping.
    :vartype target: str
    :ivar timeout: The time in seconds to wait for a reply.
    :vartype timeout: int
    """

    target: str = Field(
        ..., description="The destination IP address or hostname to ping."
    )
    timeout: int = Field(2, description="The time in seconds to wait for a reply.")


class ScapyTcpScanInput(BaseModel):
    """Input model for scanning a single TCP port.

    :ivar target: The destination IP address or hostname.
    :vartype target: str
    :ivar port: The TCP port to scan.
    :vartype port: int
    :ivar timeout: The time in seconds to wait for a reply.
    :vartype timeout: int
    """

    target: str = Field(..., description="The destination IP address or hostname.")
    port: int = Field(..., gt=0, lt=65536, description="The TCP port to scan.")
    timeout: int = Field(2, description="The time in seconds to wait for a reply.")


class ScapyLayer(BaseModel):
    """Defines a single, safe layer for packet crafting."""

    name: str = Field(
        ..., description="The name of the Scapy layer (e.g., 'IP', 'TCP')."
    )
    args: Dict[str, Any] = Field(
        default_factory=dict,
        description="A dictionary of arguments for the layer (e.g., {'dst': '8.8.8.8'}).",
    )


class ScapyCraftSendInput(BaseModel):
    """A safe input model for crafting and sending a custom packet."""

    layers: List[ScapyLayer] = Field(
        ..., description="A list of Scapy layers to construct the packet."
    )
    count: int = Field(1, description="The number of packets to send.")


class ScapyArpScanInput(BaseModel):
    """Input model for performing an ARP scan on a network range.

    :ivar target_range: The target network range in CIDR notation (e.g., '192.168.1.0/24').
    :vartype target_range: str
    :ivar timeout: The timeout in seconds for the scan.
    :vartype timeout: int
    """

    target_range: str = Field(
        ...,
        description="The target network range in CIDR notation (e.g., '192.168.1.0/24').",
    )
    timeout: int = Field(2, description="The timeout in seconds for the scan.")


class ScapySniffInput(BaseModel):
    """Input model for sniffing network packets.

    :ivar packet_count: The number of packets to capture.
    :vartype packet_count: int
    :ivar filter_bpf: Optional BPF filter string (e.g., 'tcp port 80').
    :vartype filter_bpf: Optional[str]
    :ivar timeout: The maximum time in seconds to wait for the packets.
    :vartype timeout: int
    """

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
    """Uses scapy to send an ICMP echo request and determines if the host is up.

    :param input_data: An object containing the target and timeout.
    :type input_data: ScapyPingInput
    :return: A string indicating if the host is up or down.
    :rtype: str
    :raises ToolExecutionError: If `scapy` is not installed or other scapy error occurs.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError(
            "The 'scapy' library is not installed. This tool cannot be used."
        )

    logger.info(f"Pinging host {input_data.target} with scapy.")
    try:
        packet = IP(dst=input_data.target) / ICMP()  # type: ignore
        reply = sr1(packet, timeout=input_data.timeout, verbose=0)  # type: ignore

        if reply is None:
            return f"Host {input_data.target} is down or not responding."
        else:
            return f"Host {input_data.target} is up."
    except Exception as e:  # Catch any scapy-related or other runtime errors
        logger.exception(f"scapy_ping failed for target {input_data.target}: {e}")
        raise ToolExecutionError(f"An error occurred during scapy ping: {e}")


@register_tool(
    name="scapy_tcp_scan",
    input_model=ScapyTcpScanInput,
    description="Performs a stealthy TCP SYN scan on a single port to check if it's open, closed, or filtered.",
    tags=["scapy", "network", "scan", "tcp"],
    category="network",
    safe_mode=False,
)
def scapy_tcp_scan(input_data: ScapyTcpScanInput) -> str:
    """Sends a single TCP SYN packet and analyzes the reply to determine port state.

    :param input_data: An object containing the target, port, and timeout.
    :type input_data: ScapyTcpScanInput
    :return: A string indicating if the port is open, closed, or filtered.
    :rtype: str
    :raises ToolExecutionError: If `scapy` is not installed or other scapy error occurs.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError(
            "The 'scapy' library is not installed. This tool cannot be used."
        )

    logger.info(
        f"Scanning port {input_data.port} on host {input_data.target} with scapy."
    )
    try:
        packet = IP(dst=input_data.target) / TCP(dport=input_data.port, flags="S")  # type: ignore
        response = sr1(packet, timeout=input_data.timeout, verbose=0)  # type: ignore

        if response is None:
            return f"Port {input_data.port} on {input_data.target} is filtered (No response)."
        elif response.haslayer(TCP):  # type: ignore
            if response.getlayer(TCP).flags == 0x12:  # SYN/ACK # type: ignore
                send(  # type: ignore
                    IP(dst=input_data.target) / TCP(dport=input_data.port, flags="R"),  # type: ignore
                    verbose=0,
                )
                return f"Port {input_data.port} on {input_data.target} is open."
            elif response.getlayer(TCP).flags == 0x14:  # RST/ACK # type: ignore
                return f"Port {input_data.port} on {input_data.target} is closed."
            else:  # Other flags
                return f"Port {input_data.port} on {input_data.target} received an unexpected TCP response (flags={response.getlayer(TCP).flags})."  # type: ignore

        return f"Port {input_data.port} on {input_data.target} state is unknown (unexpected response type)."
    except Exception as e:  # Catch any scapy-related or other runtime errors
        logger.exception(
            f"scapy_tcp_scan failed for {input_data.target}:{input_data.port}: {e}"
        )
        raise ToolExecutionError(f"An error occurred during TCP scan: {e}")


@register_tool(
    name="scapy_craft_and_send",
    input_model=ScapyCraftSendInput,
    description="Dynamically crafts and sends a custom packet defined by a list of layers."
    "This is a safe alternative to using eval().",
    tags=["scapy", "network", "crafting", "packet"],
    category="network",
    safe_mode=False,
)
def scapy_craft_and_send(input_data: ScapyCraftSendInput) -> str:
    """Constructs a packet from a list of structured layer objects and sends it."""
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError(
            "The 'scapy' library is not installed. This tool cannot be used."
        )

    logger.info(f"Safely crafting custom packet with layers: {input_data.layers}")

    allowed_layers = {
        "Ether": scapy.Ether,  # type: ignore
        "IP": scapy.IP,  # type: ignore
        "TCP": scapy.TCP,  # type: ignore
        "UDP": scapy.UDP,  # type: ignore
        "ICMP": scapy.ICMP,  # type: ignore
        "ARP": scapy.ARP,  # type: ignore
        "DNS": scapy.DNS,  # type: ignore
        "DNSQR": scapy.DNSQR,  # type: ignore
    }

    try:
        packet_layers = []
        for layer_data in input_data.layers:
            layer_class = allowed_layers.get(layer_data.name)
            if not layer_class:
                raise ToolExecutionError(
                    f"Packet crafting failed: Layer '{layer_data.name}' is not supported."
                )
            packet_layers.append(layer_class(**layer_data.args))

        if not packet_layers:
            raise ToolExecutionError("No layers provided for packet crafting.")

        final_packet = packet_layers[0]
        for layer in packet_layers[1:]:
            final_packet /= layer

        logger.info(f"Sending crafted packet: {final_packet.summary()}")
        send(final_packet, count=input_data.count, verbose=0)  # type: ignore

        return f"Successfully sent {input_data.count} packet(s) of type {final_packet.summary()}"
    except Exception as e:  # Catch any scapy errors or other runtime issues
        logger.exception(f"Packet crafting or sending failed: {e}")
        raise ToolExecutionError(f"Failed to craft or send packet: {e}")


@register_tool(
    name="scapy_arp_scan",
    input_model=ScapyArpScanInput,
    description="Performs an ARP scan to discover live hosts on a local network range.",
    tags=["scapy", "network", "discovery", "arp", "scan"],
    category="network",
    safe_mode=False,
)
def scapy_arp_scan(input_data: ScapyArpScanInput) -> str:
    """Uses scapy to send ARP requests to a network range and reports discovered hosts.

    :param input_data: An object containing the target range and timeout.
    :type input_data: ScapyArpScanInput
    :return: A formatted list of discovered hosts with their IP and MAC addresses.
    :rtype: str
    :raises ToolExecutionError: If `scapy` is not installed or other scapy error occurs.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError(
            "The 'scapy' library is not installed. This tool cannot be used."
        )

    logger.info(f"Performing ARP scan on network range: {input_data.target_range}")
    try:
        arp_request = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=input_data.target_range)  # type: ignore

        answered, _ = srp(arp_request, timeout=input_data.timeout, verbose=0)  # type: ignore

        if not answered:
            return f"No hosts found in range {input_data.target_range}."

        results = ["Discovered hosts:"]
        for sent, received in answered:
            results.append(f"  - IP: {received.psrc:<16} MAC: {received.hwsrc}")

        return "\n".join(results)
    except Exception as e:  # Catch any scapy-related or other runtime errors
        logger.exception(
            f"scapy_arp_scan failed for range {input_data.target_range}: {e}"
        )
        raise ToolExecutionError(f"An error occurred during ARP scan: {e}")


@register_tool(
    name="scapy_sniff",
    input_model=ScapySniffInput,
    description="Captures network packets on the local interface, with an optional filter.",
    tags=["scapy", "network", "sniffing", "pcap"],
    category="network",
    safe_mode=False,
)
def scapy_sniff(input_data: ScapySniffInput) -> str:
    """Uses scapy to sniff network traffic and returns a summary of captured packets.

    :param input_data: An object specifying packet count, filter, and timeout.
    :type input_data: ScapySniffInput
    :return: A summary of the captured packets or a 'no packets' message.
    :rtype: str
    :raises ToolExecutionError: If `scapy` is not installed or other scapy error occurs.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError(
            "The 'scapy' library is not installed. This tool cannot be used."
        )

    logger.info(
        f"Starting packet sniff for {input_data.packet_count} packets. Filter: '{input_data.filter_bpf or 'None'}'"
    )
    try:
        packets = sniff(  # type: ignore
            count=input_data.packet_count,
            filter=input_data.filter_bpf,
            timeout=input_data.timeout,
        )

        if not packets:
            return "No packets captured."

        return packets.nsummary()

    except Exception as e:  # Catch any scapy-related or other runtime errors
        logger.exception(f"scapy_sniff failed: {e}")
        raise ToolExecutionError(f"An error occurred during packet sniffing: {e}")
