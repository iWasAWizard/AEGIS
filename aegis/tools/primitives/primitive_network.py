# aegis/tools/primitives/primitive_network.py
"""
Primitive tools for basic network interactions and diagnostics.

This module contains low-level tools for performing fundamental network
operations, such as sending Wake-on-LAN packets and making flexible HTTP
requests.
"""

import subprocess
from typing import Optional, Dict, Any

import requests
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===

class WakeOnLANInput(BaseModel):
    """Input for sending a Wake-on-LAN (WoL) magic packet."""
    mac_address: str = Field(..., description="The MAC address of the target device to wake.")


class HttpRequestInput(BaseModel):
    """Input for making a generic HTTP request."""
    method: str = Field(..., description="HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE').")
    url: str = Field(..., description="The full target URL for the request.")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Optional HTTP headers.")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="URL query string parameters.")
    body: Optional[str] = Field(None, description="The raw request body as a string (for POST/PUT).")


# === Tools ===

@register_tool(
    name="send_wake_on_lan",
    input_model=WakeOnLANInput,
    tags=["network", "wol", "primitive"],
    description="Sends a Wake-on-LAN (WoL) magic packet to a specified MAC address.",
    safe_mode=True,
    purpose="Power on a remote machine that supports Wake-on-LAN.",
    category="network",
)
def send_wake_on_lan(input_data: WakeOnLANInput) -> str:
    """Uses the `wakeonlan` command-line utility to send a WoL magic packet.

    :param input_data: An object containing the target MAC address.
    :type input_data: WakeOnLANInput
    :return: A string indicating the result of the command.
    :rtype: str
    """
    logger.info(f"Sending Wake-on-LAN packet to MAC: {input_data.mac_address}")
    try:
        # The 'wakeonlan' utility must be installed on the host system.
        result = subprocess.run(
            ["wakeonlan", input_data.mac_address],
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )
        output = result.stdout.strip()
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr.strip()}"
        return output
    except FileNotFoundError:
        error_msg = "[ERROR] The 'wakeonlan' command was not found. Please install it."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        logger.exception(f"Failed to send Wake-on-LAN packet to {input_data.mac_address}")
        return f"[ERROR] Failed to send Wake-on-LAN packet: {e}"


@register_tool(
    name="http_request",
    input_model=HttpRequestInput,
    tags=["http", "network", "api", "primitive"],
    description="Sends a flexible HTTP request with full control over method, headers, body, and params.",
    safe_mode=True,  # Considered safe as it only interacts with network resources, not the local filesystem.
    purpose="Interact with web servers or REST APIs.",
    category="network",
)
def http_request(input_data: HttpRequestInput) -> str:
    """Performs a generic HTTP request using the requests library.

    :param input_data: An object containing all necessary request parameters.
    :type input_data: HttpRequestInput
    :return: A string containing the HTTP status code and response body.
    :rtype: str
    """
    method = input_data.method.upper()
    logger.info(f"Sending {method} request to {input_data.url}")
    try:
        response = requests.request(
            method=method,
            url=input_data.url,
            headers=input_data.headers,
            params=input_data.params,
            data=input_data.body.encode('utf-8') if input_data.body else None,  # requests prefers bytes for data
            timeout=30  # A reasonable default timeout
        )
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        return f"Status: {response.status_code}\nBody:\n{response.text}"
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request to {input_data.url} failed: {e}")
        return f"[ERROR] HTTP request failed: {e}"
    except Exception as e:
        logger.exception(f"An unexpected error occurred during HTTP request to {input_data.url}")
        return f"[ERROR] An unexpected error occurred: {e}"
