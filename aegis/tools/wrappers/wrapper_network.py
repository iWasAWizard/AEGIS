# aegis/tools/wrappers/wrapper_network.py
"""
Higher-level wrapper tools for common network operations.

This module provides convenient wrappers around network primitives for tasks
like sending structured JSON data, interacting with specific services like
Grafana, or running common network scans like Nmap.
"""

import json
from typing import Dict, Any, List

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


class HttpPostJsonInput(BaseModel):
    """Input for sending a POST request with a JSON payload."""

    url: str = Field(..., description="The target URL to send the POST request to.")
    payload: Dict[str, Any] = Field(
        ..., description="The JSON-serializable payload (dictionary) to send."
    )
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Optional HTTP headers."
    )


class GrafanaUploadInput(BaseModel):
    """Input for sending a payload to a Grafana API endpoint."""

    url: str = Field(
        ..., description="The Grafana API endpoint URL (e.g., for annotations or Loki)."
    )
    payload: Dict[str, Any] = Field(
        ..., description="The JSON payload to POST to Grafana."
    )
    token: str = Field(
        ...,
        description="The Grafana API key or service account token (sent as a Bearer token).",
    )


class NmapScanInput(BaseModel):
    """Input for performing an Nmap port scan."""

    targets: List[str] = Field(
        ..., description="A list of IP addresses or hostnames to scan."
    )
    ports: str = Field(
        "1-1024", description="Port range or list (e.g., '22,80,443', '1-65535')."
    )
    scan_type_flag: str = Field(
        "-sV", description="The Nmap scan type flag (e.g., -sS, -sT, -sV, -O)."
    )
    extra_flags: str = Field(
        "-T4", description="Any additional Nmap flags to include (e.g., '-T4 -Pn')."
    )


# === Tools ===


@register_tool(
    name="http_post_json",
    input_model=HttpPostJsonInput,
    tags=["wrapper", "http", "json", "api"],
    description="Sends a POST request with a JSON payload and appropriate headers.",
    safe_mode=True,
    purpose="Send structured data to a JSON-based API endpoint.",
    category="network",
)
def http_post_json(input_data: HttpPostJsonInput) -> str:
    """A convenient wrapper for sending JSON data via an HTTP POST request.

    :param input_data: An object containing the URL, payload, and optional headers.
    :type input_data: HttpPostJsonInput
    :return: The result of the HTTP request.
    :rtype: str
    """
    logger.info(f"POSTing JSON data to {input_data.url}")
    # The http_request primitive expects the body to be a string.
    json_body = json.dumps(input_data.payload)
    # Ensure the Content-Type header is set for JSON.
    headers = {"Content-Type": "application/json", **input_data.headers}

    request_input = HttpRequestInput(
        method="POST", url=input_data.url, headers=headers, body=json_body
    )
    return http_request(request_input)


@register_tool(
    name="upload_to_grafana",
    input_model=GrafanaUploadInput,
    tags=["grafana", "monitoring", "http", "wrapper"],
    description="Sends a JSON payload to a Grafana endpoint using a bearer token for authentication.",
    safe_mode=True,
    purpose="Upload data, annotations, or alerts to a Grafana instance.",
    category="integration",
)
def upload_to_grafana(input_data: GrafanaUploadInput) -> str:
    """A specialized tool for sending data to Grafana's API.

    :param input_data: An object containing the Grafana URL, payload, and auth token.
    :type input_data: GrafanaUploadInput
    :return: The result of the HTTP request to Grafana.
    :rtype: str
    """
    logger.info(f"Uploading payload to Grafana at {input_data.url}")
    json_body = json.dumps(input_data.payload)
    headers = {
        "Authorization": f"Bearer {input_data.token}",
        "Content-Type": "application/json",
    }

    request_input = HttpRequestInput(
        method="POST", url=input_data.url, headers=headers, body=json_body
    )
    return http_request(request_input)


@register_tool(
    name="nmap_port_scan",
    input_model=NmapScanInput,
    tags=["nmap", "network", "scan", "wrapper"],
    description="Performs an Nmap scan on one or more remote hosts.",
    safe_mode=True,  # Though a scanner, it is non-intrusive and does not modify state.
    purpose="Scan ports and identify services on remote targets.",
    category="network",
)
def nmap_port_scan(input_data: NmapScanInput) -> str:
    """Constructs and executes an Nmap command based on the provided parameters.

    :param input_data: An object containing targets, ports, and scan flags.
    :type input_data: NmapScanInput
    :return: The raw output of the Nmap command.
    :rtype: str
    """
    # Combine all parts into a single command string.
    targets_str = " ".join(input_data.targets)
    cmd = (
        f"nmap {input_data.scan_type_flag} "
        f"-p {input_data.ports} {input_data.extra_flags} {targets_str}"
    )
    logger.info(f"Running Nmap scan with command: {cmd}")
    # Use the local command primitive to execute the scan.
    return run_local_command(RunLocalCommandInput(command=cmd, shell=True))
