# aegis/tools/wrappers/wrapper_network.py
"""
Network wrapper tools for composing higher-level network operations.

This module provides tools that wrap network primitives to perform common,
multi-step tasks such as formatted Nmap scans or posting structured JSON data
to specific endpoints like Grafana.
"""
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.tools.primitives.primitive_network import http_request, HttpRequestInput
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class HttpPostJsonInput(BaseModel):
    """Input for posting a JSON payload to a URL.

    :ivar url: The target URL for the POST request.
    :vartype url: str
    :ivar payload: A dictionary to be sent as the JSON body.
    :vartype payload: Dict[str, Any]
    :ivar timeout: Optional timeout for this specific request in seconds.
    :vartype timeout: Optional[int]
    """

    url: str = Field(..., description="Target URL for the POST request.")
    payload: Dict[str, Any] = Field(..., description="Dictionary to send as JSON.")
    timeout: Optional[int] = Field(
        None, gt=0, description="Optional timeout in seconds for this request."
    )


class GrafanaUploadInput(HttpPostJsonInput):
    """Input for uploading an annotation to a Grafana instance.

    :ivar token: The Grafana API token for authentication.
    :vartype token: str
    """

    token: str = Field(..., description="Grafana API token for authentication.")


# === Tools ===


@register_tool(
    name="http_post_json",
    input_model=HttpPostJsonInput,
    tags=["http", "api", "wrapper"],
    description="Sends an HTTP POST request with a JSON payload.",
    safe_mode=True,
    purpose="Send a JSON payload via HTTP POST.",
    category="network",
)
def http_post_json(input_data: HttpPostJsonInput) -> str:
    """A wrapper to simplify sending JSON data via HTTP POST.

    This tool automatically serializes the payload dictionary to a JSON string
    and sets the appropriate 'Content-Type' header.

    :param input_data: An object containing the URL and payload dictionary.
    :type input_data: HttpPostJsonInput
    :return: The response from the `http_request` primitive.
    :rtype: str
    """
    headers = {"Content-Type": "application/json"}

    http_input = HttpRequestInput(
        body=None,
        method="POST",
        url=input_data.url,
        headers=headers,
        json_payload=input_data.payload,
        timeout=input_data.timeout,
    )
    return http_request(http_input)


@register_tool(
    name="upload_to_grafana",
    input_model=GrafanaUploadInput,
    tags=["http", "api", "grafana", "monitoring", "wrapper"],
    description="Uploads a Grafana annotation via its API.",
    safe_mode=True,
    purpose="Post an annotation event to a Grafana dashboard.",
    category="monitoring",
)
def upload_to_grafana(input_data: GrafanaUploadInput) -> str:
    """A specific wrapper for sending annotations to Grafana.

    This tool adds the required 'Authorization' header for Grafana API calls
    in addition to setting the 'Content-Type' for the JSON payload.

    :param input_data: An object containing URL, payload, and Grafana token.
    :type input_data: GrafanaUploadInput
    :return: The response from the `http_request` primitive.
    :rtype: str
    """
    headers = {
        "Authorization": f"Bearer {input_data.token}",
        "Content-Type": "application/json",
    }

    http_input = HttpRequestInput(
        body=None,
        method="POST",
        url=input_data.url,
        headers=headers,
        json_payload=input_data.payload,
        timeout=input_data.timeout,
    )
    return http_request(http_input)


class NmapScanInput(BaseModel):
    """Input for running a targeted Nmap port scan."""

    targets: List[str] = Field(
        ..., description="List of target IPs, hostnames, or CIDR ranges."
    )
    ports: str = Field(
        "1-1024", description="Ports to scan (e.g., '22,80,443', '1-1000')."
    )
    scan_type_flag: str = Field(
        "-sV", description="Nmap scan type flag (e.g., -sS, -sT, -sV)."
    )
    extra_flags: str = Field(
        "", description="Optional extra flags for the Nmap command."
    )


@register_tool(
    name="nmap_port_scan",
    input_model=NmapScanInput,
    tags=["network", "scan", "nmap", "wrapper"],
    description="Performs a port scan on specified targets using Nmap.",
    safe_mode=False,
    purpose="Scan target hosts for open ports and services.",
    category="network",
)
def nmap_port_scan(input_data: NmapScanInput) -> str:
    """A wrapper for the 'nmap' command-line utility."""
    from aegis.tools.primitives.primitive_system import (
        run_local_command,
        RunLocalCommandInput,
    )

    targets_str = " ".join(input_data.targets)
    command = f"nmap {input_data.scan_type_flag} -p {input_data.ports} {input_data.extra_flags} {targets_str}"

    # We must use the RunLocalCommandInput model for the primitive
    cmd_input = RunLocalCommandInput(command=command, shell=True)
    return run_local_command(cmd_input)
