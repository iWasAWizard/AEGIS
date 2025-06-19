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
from aegis.tools.primitives.primitive_system import (
    run_local_command,
    RunLocalCommandInput,
)
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class NmapScanInput(BaseModel):
    """Input for running a customized Nmap scan.

    :ivar targets: A list of hosts or IP addresses to scan.
    :vartype targets: List[str]
    :ivar ports: A comma-separated string of ports (e.g., '80,443,8080').
    :vartype ports: str
    :ivar scan_type_flag: The Nmap scan type flag (e.g., '-sS', '-sT', '-sU').
    :vartype scan_type_flag: str
    :ivar extra_flags: Any additional flags to pass to Nmap.
    :vartype extra_flags: str
    """

    targets: List[str] = Field(..., description="List of hosts or IPs to scan.")
    ports: str = Field(..., description="Comma-separated string of ports.")
    scan_type_flag: str = Field("-sT", description="Nmap scan type flag (e.g., -sS).")
    extra_flags: str = Field("", description="Additional flags for the Nmap command.")


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
    name="nmap_port_scan",
    input_model=NmapScanInput,
    tags=["network", "scan", "nmap", "wrapper"],
    description="Runs a configurable Nmap scan against specified targets and ports.",
    safe_mode=False,
    purpose="Scan network targets for open ports using Nmap.",
    category="network",
)
def nmap_port_scan(input_data: NmapScanInput) -> str:
    """Constructs and executes an Nmap command based on the provided inputs.

    :param input_data: An object containing scan targets, ports, and flags.
    :type input_data: NmapScanInput
    :return: The raw output from the Nmap command.
    :rtype: str
    """
    targets_str = " ".join(input_data.targets)
    command = f"nmap {input_data.scan_type_flag} -p {input_data.ports} {input_data.extra_flags} {targets_str}"
    logger.info(f"Executing Nmap scan: {command}")
    return run_local_command(RunLocalCommandInput(command=command, shell=True))


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
        method="POST",
        url=input_data.url,
        headers=headers,
        json_payload=input_data.payload,
        timeout=input_data.timeout,
    )
    return http_request(http_input)
