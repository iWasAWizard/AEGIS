# aegis/executors/scapy_exec.py
"""
Provides a client for performing typical Scapy-based network tasks safely.
"""
from typing import List, Dict, Any, Optional

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time
import json

logger = setup_logger(__name__)

try:
    from scapy.all import ICMP, IP, TCP, ARP, Ether, sr1, sr, sniff, send

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


class ScapyExecutor:
    """A client to encapsulate Scapy interactions with safer defaults."""

    def __init__(self, require_root: bool = False):
        """
        :param require_root: If True, raise if the process is not root; otherwise warn.
        :type require_root: bool
        """
        if not SCAPY_AVAILABLE:
            raise ToolExecutionError("Scapy is not installed.")
        try:
            import os

            if require_root and os.geteuid() != 0:
                raise ConfigurationError("Scapy operations require root privileges.")
            if os.geteuid() != 0:
                logger.warning("Scapy running without root; some operations may fail.")
        except Exception as e:
            raise ToolExecutionError(f"Environment check failed: {e}") from e

    def ping(
        self, target_ip: str, count: int = 1, timeout_s: int = 2
    ) -> Dict[str, Any]:
        """
        Send ICMP echo requests to a target and measure success.
        """
        try:
            results = {"sent": count, "received": 0, "rtts_ms": []}
            for _ in range(count):
                pkt = IP(dst=target_ip) / ICMP()
                ans = sr1(pkt, timeout=timeout_s, verbose=False)
                if ans is not None:
                    results["received"] += 1
                    rtt_ms = (
                        (ans.time - pkt.time) * 1000.0 if hasattr(ans, "time") else None
                    )
                    if rtt_ms is not None:
                        results["rtts_ms"].append(rtt_ms)
            return results
        except Exception as e:
            raise ToolExecutionError(f"Scapy ping error: {e}") from e

    def tcp_scan(
        self, target_ip: str, ports: List[int], timeout_s: int = 2
    ) -> Dict[str, Any]:
        """
        Perform a very basic TCP SYN scan over a list of ports.
        """
        try:
            results: Dict[str, str] = {}
            for p in ports:
                syn = IP(dst=target_ip) / TCP(dport=p, flags="S")
                ans, _ = sr(syn, timeout=timeout_s, verbose=False)
                state = "filtered"
                if ans:
                    for _, rcv in ans:
                        if rcv.haslayer(TCP) and rcv[TCP].flags == 0x12:
                            state = "open"
                            break
                        elif rcv.haslayer(TCP) and rcv[TCP].flags == 0x14:
                            state = "closed"
                            break
                results[str(p)] = state
            return {"host": target_ip, "results": results}
        except Exception as e:
            raise ToolExecutionError(f"Scapy TCP scan error: {e}") from e

    def arp_scan(self, network_cidr: str, timeout_s: int = 2) -> List[Dict[str, str]]:
        """
        Perform an ARP scan over a local network CIDR.
        """
        try:
            pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network_cidr)
            ans, _ = sr(pkt, timeout=timeout_s, verbose=False)
            hosts: List[Dict[str, str]] = []
            if ans:
                for _, rcv in ans:
                    hosts.append({"ip": rcv.psrc, "mac": rcv.hwsrc})
            return hosts
        except Exception as e:
            raise ToolExecutionError(f"Scapy ARP scan error: {e}") from e

    def sniff_packets(
        self,
        iface: Optional[str] = None,
        count: int = 10,
        timeout_s: int = 5,
        bpf_filter: Optional[str] = None,
    ) -> List[str]:
        """
        Sniff packets and return a simple string summary list.
        """
        try:
            pkts = sniff(iface=iface, count=count, timeout=timeout_s, filter=bpf_filter)
            return [p.summary() for p in pkts]
        except Exception as e:
            raise ToolExecutionError(f"Scapy sniff error: {e}") from e

    def craft_and_send_packet(
        self,
        dst_ip: str,
        dst_port: int | None = None,
        payload: bytes | str | None = None,
        protocol: str = "ICMP",
    ) -> bool:
        """
        Craft and send a very simple packet via Scapy (ICMP default).
        """
        try:
            if protocol.upper() == "ICMP":
                pkt = IP(dst=dst_ip) / ICMP()
            elif protocol.upper() == "TCP" and dst_port is not None:
                pkt = IP(dst=dst_ip) / TCP(dport=dst_port, flags="S")
                if payload:
                    if isinstance(payload, str):
                        payload = payload.encode("utf-8", "ignore")
                    pkt = pkt / payload
            else:
                raise ToolExecutionError(
                    "Unsupported protocol for craft_and_send_packet."
                )
            send(pkt, verbose=False)
            return True
        except Exception as e:
            raise ToolExecutionError(f"Scapy craft/send error: {e}") from e


# === ToolResult wrappers ===
def _now_ms() -> int:
    return int(time.time() * 1000)


def _error_type_from_exception(e: Exception) -> str:
    msg = str(e).lower()
    if "timeout" in msg:
        return "Timeout"
    if "permission" in msg or "auth" in msg:
        return "Auth"
    if "not found" in msg or "no such" in msg:
        return "NotFound"
    if "parse" in msg or "json" in msg:
        return "Parse"
    return "Runtime"


class ScapyExecutorToolResultMixin:
    def ping_result(
        self, target_ip: str, count: int = 1, timeout_s: int = 2
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="scapy.ping",
                args=redact_for_log({"target_ip": target_ip, "count": count}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] scapy.ping",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.ping(target_ip=target_ip, count=count, timeout_s=timeout_s)
            return ToolResult.ok_result(
                stdout=json.dumps(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"target_ip": target_ip, "count": count},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"target_ip": target_ip, "count": count},
            )

    def tcp_scan_result(
        self, target_ip: str, ports: list[int], timeout_s: int = 2
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="scapy.tcp_scan",
                args=redact_for_log({"target_ip": target_ip, "ports": ports}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] scapy.tcp_scan",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.tcp_scan(target_ip=target_ip, ports=ports, timeout_s=timeout_s)
            return ToolResult.ok_result(
                stdout=json.dumps(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"target_ip": target_ip, "ports": ports},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"target_ip": target_ip, "ports": ports},
            )

    def arp_scan_result(self, network_cidr: str, timeout_s: int = 2) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="scapy.arp_scan",
                args=redact_for_log({"network_cidr": network_cidr}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] scapy.arp_scan",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.arp_scan(network_cidr=network_cidr, timeout_s=timeout_s)
            return ToolResult.ok_result(
                stdout=json.dumps(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"network_cidr": network_cidr},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"network_cidr": network_cidr},
            )

    def sniff_packets_result(
        self,
        iface: str | None = None,
        count: int = 10,
        timeout_s: int = 5,
        bpf_filter: str | None = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="scapy.sniff",
                args=redact_for_log({"iface": iface, "count": count}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] scapy.sniff",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.sniff_packets(
                iface=iface, count=count, timeout_s=timeout_s, bpf_filter=bpf_filter
            )
            return ToolResult.ok_result(
                stdout=json.dumps(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"iface": iface, "count": count},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"iface": iface, "count": count},
            )

    def craft_and_send_packet_result(
        self,
        dst_ip: str,
        dst_port: int | None = None,
        payload: bytes | str | None = None,
        protocol: str = "ICMP",
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="scapy.send",
                args=redact_for_log(
                    {"dst_ip": dst_ip, "dst_port": dst_port, "protocol": protocol}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] scapy.send",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.craft_and_send_packet(
                dst_ip=dst_ip, dst_port=dst_port, payload=payload, protocol=protocol
            )
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"dst_ip": dst_ip, "dst_port": dst_port, "protocol": protocol},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"dst_ip": dst_ip, "dst_port": dst_port, "protocol": protocol},
            )


ScapyExecutor.ping_result = ScapyExecutorToolResultMixin.ping_result
ScapyExecutor.tcp_scan_result = ScapyExecutorToolResultMixin.tcp_scan_result
ScapyExecutor.arp_scan_result = ScapyExecutorToolResultMixin.arp_scan_result
ScapyExecutor.sniff_packets_result = ScapyExecutorToolResultMixin.sniff_packets_result
ScapyExecutor.craft_and_send_packet_result = (
    ScapyExecutorToolResultMixin.craft_and_send_packet_result
)
