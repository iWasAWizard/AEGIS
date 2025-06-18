# aegis/tools/primitives/primitive_network.py
"""
Primitive tools for basic network interactions and diagnostics.

This module contains low-level tools for performing fundamental network
operations, such as sending Wake-on-LAN packets, making flexible HTTP
requests, and checking TCP port status.
"""

import socket
import subprocess
from typing import Optional, Dict, Any

import requests
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class WakeOnLANInput(BaseModel):
    """Input for sending a Wake-on-LAN (WoL) magic packet.

    :ivar mac_address: The MAC address of the target device to wake.
    :vartype mac_address: str
    """

    mac_address: str = Field(
        ..., description="The MAC address of the target device to wake."
    )


class HttpRequestInput(BaseModel):
    """Input for making a generic HTTP request.

    :ivar method: HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE').
    :vartype method: str
    :ivar url: The full target URL for the request.
    :vartype url: str
    :ivar headers: Optional HTTP headers.
    :vartype headers: Optional[Dict[str, str]]
    :ivar params: URL query string parameters.
    :vartype params: Optional[Dict[str, Any]]
    :ivar body: The raw request body as a string (for POST/PUT).
    :vartype body: Optional[str]
    """

    method: str = Field(
        ..., description="HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE')."
    )
    url: str = Field(..., description="The full target URL for the request.")
    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Optional HTTP headers."
    )
    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="URL query string parameters."
    )
    body: Optional[str] = Field(
        None, description="The raw request body as a string (for POST/PUT)."
    )


class CheckPortStatusInput(BaseModel):
    """Input for checking if a specific TCP port is open on a host.

    :ivar host: The hostname or IP address to check.
    :vartype host: str
    :ivar port: The port number to check.
    :vartype port: int
    :ivar timeout: Connection timeout in seconds.
    :vartype timeout: float
    """

    host: str = Field("127.0.0.1", description="The hostname or IP address to check.")
    port: int = Field(..., gt=0, lt=65536, description="The port number to check.")
    timeout: float = Field(2.0, description="Connection timeout in seconds.")


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
    :raises ToolExecutionError: If the `wakeonlan` command is not found, times out, or fails.
    """
    logger.info(f"Sending Wake-on-LAN packet to MAC: {input_data.mac_address}")
    try:
        result = subprocess.run(
            ["wakeonlan", input_data.mac_address],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,  # Check returncode manually
        )
        output = result.stdout.strip()
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr.strip()}"

        if result.returncode != 0:
            logger.error(
                f"'wakeonlan' command failed for MAC {input_data.mac_address} with RC {result.returncode}. Output: {output}"
            )
            raise ToolExecutionError(
                f"'wakeonlan' command failed with RC {result.returncode}. Output: {output}"
            )

        logger.info(
            f"'wakeonlan' command successful for MAC {input_data.mac_address}. Output: {output if output else 'No output.'}"
        )
        return (
            output
            if output
            else f"Wake-on-LAN packet sent to {input_data.mac_address}."
        )
    except FileNotFoundError:
        error_msg = "'wakeonlan' command was not found. Please ensure it is installed and in PATH."
        logger.error(error_msg)
        raise ToolExecutionError(error_msg)
    except subprocess.TimeoutExpired:
        logger.warning(
            f"'wakeonlan' command timed out for MAC {input_data.mac_address}."
        )
        raise ToolExecutionError(
            f"'wakeonlan' command timed out for MAC {input_data.mac_address}."
        )
    except Exception as e:
        logger.exception(
            f"Failed to send Wake-on-LAN packet to {input_data.mac_address}"
        )
        raise ToolExecutionError(
            f"Failed to send Wake-on-LAN packet to {input_data.mac_address}: {e}"
        )


@register_tool(
    name="http_request",
    input_model=HttpRequestInput,
    tags=["http", "network", "api", "primitive"],
    description="Sends a flexible HTTP request with full control over method, headers, body, and params.",
    safe_mode=True,
    purpose="Interact with web servers or REST APIs.",
    category="network",
)
def http_request(input_data: HttpRequestInput) -> str:
    """Performs a generic HTTP request using the requests library.

    :param input_data: An object containing all necessary request parameters.
    :type input_data: HttpRequestInput
    :return: A string containing the HTTP status code and response body.
    :rtype: str
    :raises ToolExecutionError: If the HTTP request fails due to network or server issues.
    """
    method = input_data.method.upper()
    logger.info(f"Sending {method} request to {input_data.url}")
    try:
        response = requests.request(
            method=method,
            url=input_data.url,
            headers=input_data.headers,
            params=input_data.params,
            data=(input_data.body.encode("utf-8") if input_data.body else None),
            timeout=30,
        )
        response.raise_for_status()  # This will raise an HTTPError for bad responses (4xx or 5xx)
        return f"Status: {response.status_code}\nBody:\n{response.text}"
    except (
        requests.exceptions.RequestException
    ) as e:  # Catches connection errors, timeouts, HTTPError, etc.
        logger.error(f"HTTP request to {input_data.url} failed: {e}")
        raise ToolExecutionError(f"HTTP request failed: {e}")


@register_tool(
    name="check_port_status",
    input_model=CheckPortStatusInput,
    tags=["network", "port", "check", "primitive"],
    description="Checks if a specific TCP port is open on a given host.",
    safe_mode=True,
    purpose="Determine if a TCP port is open or closed on a host.",
    category="network",
)
def check_port_status(input_data: CheckPortStatusInput) -> str:
    """Attempts to establish a socket connection to a host and port to determine if it's open.

    :param input_data: An object containing the host, port, and timeout.
    :type input_data: CheckPortStatusInput
    :return: A string indicating whether the port is "Open", "Closed".
    :rtype: str
    :raises ToolExecutionError: If hostname resolution or other socket errors occur.
    """
    host, port, timeout = input_data.host, input_data.port, input_data.timeout
    logger.info(f"Checking port status for {host}:{port} with a {timeout}s timeout.")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            if s.connect_ex((host, port)) == 0:
                logger.info(f"Connection to {host}:{port} successful. Port is open.")
                return f"Port {port} on {host} is Open."
            else:
                logger.info(
                    f"Connection to {host}:{port} failed or timed out. Port is closed or filtered."
                )
                return f"Port {port} on {host} is Closed or Filtered."
    except socket.gaierror as e:
        error_msg = f"Hostname '{host}' could not be resolved: {e}"
        logger.error(error_msg)
        raise ToolExecutionError(error_msg)
    except socket.timeout:  # Specific exception for socket timeout
        error_msg = f"Connection to {host}:{port} timed out after {timeout}s."
        logger.warning(error_msg)
        # For port scanning, a timeout often implies filtered, so we can return this info
        # Or, choose to raise ToolExecutionError. Let's be informative for this tool.
        return f"Port {port} on {host} is Filtered (Connection Timed Out)."
    except socket.error as e:
        error_msg = f"A socket error occurred while checking {host}:{port}: {e}"
        logger.error(error_msg)
        raise ToolExecutionError(error_msg)
