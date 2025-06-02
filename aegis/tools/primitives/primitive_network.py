"""
Primitive tools for basic network interactions and diagnostics.

Includes functions like ICMP ping, TCP port checks, and hostname resolution.
"""

import subprocess
from typing import Optional, Dict, Any

import requests
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class WakeOnLANInput(BaseModel):
    """
    WakeOnLANInput class.
    """

    mac_address: str = Field(description="MAC address to wake via WoL.")


class HttpRequestInput(BaseModel):
    """
    HttpRequestInput class.
    """

    method: str = Field(
        description="HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)."
    )
    url: str = Field(description="The full target URL.")
    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="HTTP headers to send."
    )
    params: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Query string parameters."
    )
    body: Optional[str] = Field(
        default=None, description="Raw string body to send (not JSON-encoded)."
    )
    data: Optional[Any] = Field(
        default=None,
        description="WebRequest content destined for the target HTTP server.",
    )


@register_tool(
    name="send_wake_on_lan",
    input_model=WakeOnLANInput,
    tags=["network", "wol", "primitive"],
    description="Send a Wake-on-LAN magic packet to a MAC address.",
    safe_mode=True,
    purpose="Send a WoL packet to a powered-off machine to wake it up.",
    category="network",
)
def send_wake_on_lan(input_data: WakeOnLANInput) -> str:
    """
    send_wake_on_lan.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"Sending Wake-on-LAN packet to MAC {input_data.mac_address}")
    try:
        result = subprocess.run(
            ["wakeonlan", input_data.mac_address],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() + (
            "\n" + result.stderr.strip() if result.stderr else ""
        )
    except Exception as e:
        logger.exception(f"[primitive_network] Error: {e}")
        return f"[ERROR] Failed to send Wake-on-LAN: {str(e)}"


@register_tool(
    name="http_request",
    input_model=HttpRequestInput,
    tags=["http", "primitive", "network", "flexible"],
    description="Send a raw HTTP request with full control over method, headers, body, and query params.",
    safe_mode=True,
    purpose="Allow flexible HTTP access for tools that need to interact with APIs using various formats.",
    category="network",
)
def http_request(input_data: HttpRequestInput) -> str:
    """
    http_request.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"Sending {input_data.method.upper()} request to {input_data.url}")
    try:
        response = requests.request(
            method=input_data.method.upper(),
            url=input_data.url,
            headers=input_data.headers,
            params=input_data.params,
            data=input_data.body,
        )
        return f"Status: {response.status_code}\nBody: {response.text}"
    except Exception as e:
        logger.exception(f"[primitive_network] Error: {e}")
        return f"[ERROR] Failed HTTP request: {str(e)}"
