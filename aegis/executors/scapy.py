# aegis/executors/scapy.py
"""
Provides a client for executing scapy-based network operations.
"""
from typing import List, Any, Optional, Dict

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    # Correct, explicit imports from scapy submodules
    from scapy.layers.inet import IP, TCP, UDP, ICMP
    from scapy.layers.l2 import Ether, ARP
    from scapy.layers.dns import DNS, DNSQR
    from scapy.sendrecv import sr1, srp, send, sniff

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


class ScapyExecutor:
    """A client for managing and executing scapy network operations."""

    def __init__(self, default_timeout: int = 2):
        if not SCAPY_AVAILABLE:
            raise ToolExecutionError("Scapy library is not installed.")
        self.default_timeout = default_timeout

    def ping(self, target: str, timeout: Optional[int] = None) -> str:
        """Sends an ICMP echo request to a target."""
        effective_timeout = timeout if timeout is not None else self.default_timeout
        logger.info(f"Pinging host {target} with scapy.")
        try:
            packet = IP(dst=target) / ICMP()
            reply = sr1(packet, timeout=effective_timeout, verbose=0)
            return (
                f"Host {target} is up."
                if reply
                else f"Host {target} is down or not responding."
            )
        except Exception as e:
            raise ToolExecutionError(f"An error occurred during scapy ping: {e}")

    def tcp_scan(self, target: str, port: int, timeout: Optional[int] = None) -> str:
        """Performs a TCP SYN scan on a single port."""
        effective_timeout = timeout if timeout is not None else self.default_timeout
        logger.info(f"Scanning port {port} on host {target} with scapy.")
        try:
            packet = IP(dst=target) / TCP(dport=port, flags="S")
            response = sr1(packet, timeout=effective_timeout, verbose=0)

            if response is None:
                return f"Port {port} on {target} is filtered (No response)."
            elif response.haslayer(TCP):
                tcp_layer = response.getlayer(TCP)
                if tcp_layer is not None and tcp_layer.flags == 0x12:  # SYN/ACK
                    send(IP(dst=target) / TCP(dport=port, flags="R"), verbose=0)
                    return f"Port {port} on {target} is open."
                elif tcp_layer is not None and tcp_layer.flags == 0x14:  # RST/ACK
                    return f"Port {port} on {target} is closed."
            return f"Port {port} on {target} state is unknown (unexpected response)."
        except Exception as e:
            raise ToolExecutionError(f"An error occurred during TCP scan: {e}")

    def arp_scan(self, target_range: str, timeout: Optional[int] = None) -> str:
        """Performs an ARP scan on a local network range."""
        effective_timeout = timeout if timeout is not None else self.default_timeout
        logger.info(f"Performing ARP scan on network range: {target_range}")
        try:
            arp_request = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=target_range)
            answered, _ = srp(arp_request, timeout=effective_timeout, verbose=0)

            if not answered:
                return f"No hosts found in range {target_range}."

            results = ["Discovered hosts:"]
            for _, received in answered:
                results.append(f"  - IP: {received.psrc:<16} MAC: {received.hwsrc}")
            return "\n".join(results)
        except Exception as e:
            raise ToolExecutionError(f"An error occurred during ARP scan: {e}")

    def sniff_packets(self, count: int, filter_bpf: Optional[str], timeout: int) -> str:
        """Captures network packets."""
        logger.info(
            f"Starting packet sniff for {count} packets. Filter: '{filter_bpf or 'None'}'"
        )
        try:
            packets = sniff(count=count, filter=filter_bpf, timeout=timeout)
            return str(packets.nsummary()) if packets else "No packets captured."
        except Exception as e:
            raise ToolExecutionError(f"An error occurred during packet sniffing: {e}")

    def craft_and_send_packet(
        self, layers_data: List[Dict[str, Any]], count: int
    ) -> str:
        """Dynamically crafts and sends a custom packet."""
        logger.info(f"Safely crafting custom packet with layers: {layers_data}")
        allowed_layers = {
            "Ether": Ether,
            "IP": IP,
            "TCP": TCP,
            "UDP": UDP,
            "ICMP": ICMP,
            "ARP": ARP,
            "DNS": DNS,
            "DNSQR": DNSQR,
        }
        try:
            packet_layers = []
            for layer_data in layers_data:
                layer_class = allowed_layers.get(layer_data["name"])
                if not layer_class:
                    raise ToolExecutionError(
                        f"Layer '{layer_data['name']}' is not supported."
                    )
                packet_layers.append(layer_class(**layer_data["args"]))

            if not packet_layers:
                raise ToolExecutionError("No layers provided for packet crafting.")

            final_packet = packet_layers[0]
            for layer in packet_layers[1:]:
                final_packet /= layer

            send(final_packet, count=count, verbose=0)
            return (
                f"Successfully sent {count} packet(s) of type {final_packet.summary()}"
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to craft or send packet: {e}")
