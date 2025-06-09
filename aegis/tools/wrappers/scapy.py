# aegis/tools/wrappers/scapy.py
"""
Wrapper tools for leveraging the 'scapy' library for network packet
crafting, sending, and analysis.

These tools provide a structured interface to scapy's powerful networking
capabilities, allowing the agent to perform low-level network tasks like
pinging, port scanning, and custom packet generation.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

try:
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
    target: str = Field(..., description="The destination IP address or hostname to ping.")
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


class ScapyCraftSendInput(BaseModel):
    """Input model for crafting and sending a custom packet.

    :ivar layers: A list of scapy layer definitions as strings, from outermost to
                  innermost (e.g., ["Ether()", "IP(dst='1.1.1.1')", "UDP(dport=53)"]).
    :vartype layers: List[str]
    :ivar count: The number of packets to send.
    :vartype count: int
    """
    layers: List[str] = Field(...,
                              description="A list of scapy layer definitions as strings, from outermost to innermost (e.g., [\"Ether()\", \"IP(dst='1.1.1.1')\", \"UDP(dport=53)\"]).")
    count: int = Field(1, description="The number of packets to send.")


class ScapyArpScanInput(BaseModel):
    """Input model for performing an ARP scan on a network range.

    :ivar target_range: The target network range in CIDR notation (e.g., '192.168.1.0/24').
    :vartype target_range: str
    :ivar timeout: The timeout in seconds for the scan.
    :vartype timeout: int
    """
    target_range: str = Field(..., description="The target network range in CIDR notation (e.g., '192.168.1.0/24').")
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
    filter_bpf: Optional[str] = Field(None, description="Optional BPF filter string (e.g., 'tcp port 80').")
    timeout: int = Field(20, description="The maximum time in seconds to wait for the packets.")


# --- Tools ---

@register_tool(
    name="scapy_ping",
    input_model=ScapyPingInput,
    description="Sends a single ICMP (ping) packet to a target to check for reachability.",
    tags=["scapy", "network", "scan", "icmp"],
    category="network",
    safe_mode=False,  # Sends packets on the network
)
def scapy_ping(input_data: ScapyPingInput) -> str:
    """Uses scapy to send an ICMP echo request and determines if the host is up.

    :param input_data: An object containing the target and timeout.
    :type input_data: ScapyPingInput
    :return: A string indicating if the host is up or down.
    :rtype: str
    :raises ToolExecutionError: If the `scapy` library is not installed.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")

    logger.info(f"Pinging host {input_data.target} with scapy.")
    try:
        packet = IP(dst=input_data.target) / ICMP()
        reply = sr1(packet, timeout=input_data.timeout, verbose=0)

        if reply is None:
            return f"Host {input_data.target} is down or not responding."
        else:
            return f"Host {input_data.target} is up."
    except Exception as e:
        logger.exception(f"scapy_ping failed for target {input_data.target}: {e}")
        return f"[ERROR] An error occurred during ping: {e}"


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
    :raises ToolExecutionError: If the `scapy` library is not installed.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")

    logger.info(f"Scanning port {input_data.port} on host {input_data.target} with scapy.")
    try:
        packet = IP(dst=input_data.target) / TCP(dport=input_data.port, flags="S")
        response = sr1(packet, timeout=input_data.timeout, verbose=0)

        if response is None:
            return f"Port {input_data.port} on {input_data.target} is filtered (No response)."
        elif response.haslayer(TCP):
            if response.getlayer(TCP).flags == 0x12:  # SYN/ACK
                # Send a RST to gracefully close the connection
                send(IP(dst=input_data.target) / TCP(dport=input_data.port, flags="R"), verbose=0)
                return f"Port {input_data.port} on {input_data.target} is open."
            elif response.getlayer(TCP).flags == 0x14:  # RST/ACK
                return f"Port {input_data.port} on {input_data.target} is closed."

        return f"Port {input_data.port} on {input_data.target} state is unknown."
    except Exception as e:
        logger.exception(f"scapy_tcp_scan failed for {input_data.target}:{input_data.port}: {e}")
        return f"[ERROR] An error occurred during TCP scan: {e}"


@register_tool(
    name="scapy_craft_and_send",
    input_model=ScapyCraftSendInput,
    description="Dynamically crafts and sends a custom packet defined by a list of layers.",
    tags=["scapy", "network", "crafting", "packet"],
    category="network",
    safe_mode=False,
)
def scapy_craft_and_send(input_data: ScapyCraftSendInput) -> str:
    """Constructs a packet from a list of string-defined layers and sends it.

    This tool uses `eval()` to interpret the layer strings, giving the LLM
    full flexibility to craft complex packets. This is a powerful but
    potentially dangerous capability.

    :param input_data: An object containing the list of layers and packet count.
    :type input_data: ScapyCraftSendInput
    :return: A confirmation message of the sent packet.
    :rtype: str
    :raises ToolExecutionError: If the `scapy` library is not installed.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")

    logger.info(f"Crafting custom packet with layers: {input_data.layers}")

    try:
        packet = eval("/".join(input_data.layers), {"__builtins__": None}, scapy.all.__dict__)

        logger.info(f"Sending crafted packet: {packet.summary()}")
        send(packet, count=input_data.count, verbose=0)

        return f"Successfully sent {input_data.count} packet(s) of type {packet.summary()}"
    except Exception as e:
        logger.exception(f"Packet crafting or sending failed: {e}")
        return f"[ERROR] Failed to craft or send packet: {e}"


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
    :raises ToolExecutionError: If the `scapy` library is not installed.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")

    logger.info(f"Performing ARP scan on network range: {input_data.target_range}")
    try:
        arp_request = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=input_data.target_range)

        answered, _ = srp(arp_request, timeout=input_data.timeout, verbose=0)

        if not answered:
            return f"No hosts found in range {input_data.target_range}."

        results = ["Discovered hosts:"]
        for sent, received in answered:
            results.append(f"  - IP: {received.psrc:<16} MAC: {received.hwsrc}")

        return "\n".join(results)
    except Exception as e:
        logger.exception(f"scapy_arp_scan failed for range {input_data.target_range}: {e}")
        return f"[ERROR] An error occurred during ARP scan: {e}"


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
    :raises ToolExecutionError: If the `scapy` library is not installed.
    """
    if not SCAPY_AVAILABLE:
        raise ToolExecutionError("The 'scapy' library is not installed.")

    logger.info(
        f"Starting packet sniff for {input_data.packet_count} packets. Filter: '{input_data.filter_bpf or 'None'}'")
    try:
        packets = sniff(
            count=input_data.packet_count,
            filter=input_data.filter_bpf,
            timeout=input_data.timeout
        )

        if not packets:
            return "No packets captured."

        # Use the built-in summary method from scapy's PacketList
        return packets.nsummary()

    except Exception as e:
        logger.exception(f"scapy_sniff failed: {e}")
        return f"[ERROR] An error occurred during packet sniffing: {e}"
