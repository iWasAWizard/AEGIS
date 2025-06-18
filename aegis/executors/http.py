# aegis/executors/http.py
"""
Provides a client for making HTTP requests.
"""
from typing import Optional, Dict, Any

import requests

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class HttpExecutor:
    """A client for making HTTP requests consistently."""

    def __init__(self, default_timeout: int = 30):
        """
        Initializes the HttpExecutor.

        :param default_timeout: Default timeout in seconds for HTTP requests.
        :type default_timeout: int
        """
        self.default_timeout = default_timeout

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[str | bytes] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Performs an HTTP request.

        :param method: HTTP method (e.g., 'GET', 'POST').
        :type method: str
        :param url: The target URL.
        :type url: str
        :param headers: Optional HTTP headers.
        :type headers: Optional[Dict[str, str]]
        :param params: Optional URL query parameters.
        :type params: Optional[Dict[str, Any]]
        :param data: Optional raw request body (e.g., for form data or plain text).
        :type data: Optional[str | bytes]
        :param json_payload: Optional dictionary to send as JSON payload.
                             If provided, 'Content-Type: application/json' is set automatically
                             unless already in headers. 'data' should be None if this is used.
        :type json_payload: Optional[Dict[str, Any]]
        :param timeout: Optional timeout for this specific request.
        :type timeout: Optional[int]
        :return: The `requests.Response` object.
        :rtype: requests.Response
        :raises ToolExecutionError: If the request fails due to network issues,
                                    bad status codes (4xx, 5xx), or other request exceptions.
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout

        if data is not None and json_payload is not None:
            raise ValueError("Cannot provide both 'data' and 'json_payload'.")

        final_headers = headers.copy() if headers else {}
        if json_payload is not None and "Content-Type" not in final_headers:
            final_headers["Content-Type"] = "application/json"

        logger.debug(
            f"HttpExecutor: Sending {method.upper()} request to {url} with timeout {effective_timeout}s. "
            f"Headers: {final_headers}, Params: {params}, JSON: {json_payload is not None}, Data: {data is not None}"
        )

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=final_headers,
                params=params,
                data=data,
                json=json_payload,
                timeout=effective_timeout,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request to {url} failed: {e}")
            raise ToolExecutionError(f"HTTP request failed: {e}")
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred during HTTP request to {url}"
            )
            raise ToolExecutionError(
                f"Unexpected error during HTTP request to {url}: {e}"
            )
