import json
from typing import Dict, Any, List

import requests
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.tools.primitives import http_request, HttpRequestInput
from aegis.tools.primitives import run_local_command, RunLocalCommandInput
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class HttpPostJsonInput(BaseModel):
    """
    HttpPostJsonInput class.
    """

    url: str = Field(description="The target URL to send the POST request to.")
    payload: Dict[str, Any] = Field(
        description="The JSON-serializable payload to send."
    )
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Optional HTTP headers."
    )


class GrafanaUploadInput(BaseModel):
    """
    GrafanaUploadInput class.
    """

    url: str = Field(description="Grafana API endpoint URL.")
    payload: Dict[str, Any] = Field(description="Payload to POST to Grafana.")
    token: str = Field(description="Grafana Bearer token.")


class NmapScanInput(BaseModel):
    """
    NmapScanInput class.
    """

    target: List[str] = Field(description="IP address or hostname to scan.")
    ports: str = Field(
        default="1-1024", description="Port range or list (e.g. '22,80,443')."
    )
    additional_flags: str = Field(default="-T4", description="Additional Nmap flags.")


class HttpPostInput(BaseModel):
    """
    HttpPostInput class.
    """

    url: str = Field(..., description="Target URL to send the POST request to.")
    payload: dict = Field(
        ..., description="JSON payload to include in the POST request."
    )
    headers: dict = Field(
        default_factory=dict, description="Optional HTTP headers to include."
    )


@register_tool(
    name="http_post_json_structured",
    input_model=HttpPostJsonInput,
    tags=["wrapper", "http", "json"],
    description="Send a POST request with a JSON payload and Content-Type headers.",
    safe_mode=True,
    purpose="Simplify sending structured data to JSON-based APIs.",
    category="network",
)
def http_post_json_structured(input_data: HttpPostJsonInput) -> str:
    """
    http_post_json_structured.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"POSTing JSON to {input_data.url}")
    try:
        return http_request(
            HttpRequestInput(
                method="POST",
                url=input_data.url,
                headers={**input_data.headers, "Content-Type": "application/json"},
                params={},
                data=json.dumps(input_data.payload),
            )
        )
    except Exception as e:
        logger.exception("[http_post_json_structured] Error")
        return f"[ERROR] Could not send structured POST request: {e}"


@register_tool(
    name="upload_to_grafana",
    input_model=GrafanaUploadInput,
    tags=["grafana", "monitoring", "wrapper", "http"],
    description="Send a JSON payload to a Grafana endpoint using a bearer token.",
    safe_mode=True,
    purpose="Upload data or alerts to Grafana Cloud or On-Prem instance.",
    category="integration",
)
def upload_to_grafana(input_data: GrafanaUploadInput) -> str:
    """
    upload_to_grafana.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"Uploading payload to Grafana at {input_data.url}")
    try:
        return http_request(
            HttpRequestInput(
                method="POST",
                url=input_data.url,
                headers={
                    "Authorization": f"Bearer {input_data.token}",
                    "Content-Type": "application/json",
                },
                params={},
                data=json.dumps(input_data.payload),
            )
        )
    except Exception as e:
        logger.exception("[upload_to_grafana] Error")
        return f"[ERROR] Failed to upload to Grafana: {e}"


@register_tool(
    name="nmap_port_scan",
    input_model=NmapScanInput,
    tags=["nmap", "network", "scanner", "wrapper"],
    description="Perform an Nmap scan on a remote host.",
    safe_mode=True,
    purpose="Scan ports and identify services on a remote target.",
    category="network",
)
def nmap_port_scan(input_data: NmapScanInput) -> str:
    """
    nmap_port_scan.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    cmd = f"nmap -p {input_data.ports} {input_data.additional_flags} {' '.join(input_data.target)}"
    logger.info(f"Running Nmap scan: {cmd}")
    return run_local_command(RunLocalCommandInput(command=cmd))


@register_tool(
    name="http_post_json",
    input_model=HttpPostInput,
    description="Send a JSON payload via POST to a given URL.",
    tags=["network", "integration"],
    category="wrapper",
    timeout=10,
    retries=1,
    safe_mode=True,
)
def http_post_json(input_data: HttpPostInput) -> str:
    """
    http_post_json.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    try:
        response = requests.post(
            input_data.url,
            json=input_data.payload,
            headers=input_data.headers,
            timeout=5,
        )
        response.raise_for_status()
        return f"✅ POST to {input_data.url} succeeded: {response.status_code}"
    except Exception as e:
        logger.exception("[http_post_json] Error")
        return f"❌ POST request failed: {e}"
