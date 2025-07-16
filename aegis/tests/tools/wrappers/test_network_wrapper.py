# aegis/tests/tools/wrappers/test_network_wrapper.py
"""
Unit tests for the high-level network wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.primitives.primitive_network import HttpRequestInput
from aegis.tools.wrappers.wrapper_network import (
    http_post_json,
    HttpPostJsonInput,
    upload_to_grafana,
    GrafanaUploadInput,
)


@pytest.fixture
def mock_http_request_primitive(monkeypatch):
    """Mocks the underlying http_request primitive."""
    mock = MagicMock(return_value="HTTP OK from primitive")
    monkeypatch.setattr("aegis.tools.wrappers.wrapper_network.http_request", mock)
    return mock


# --- Tests ---


def test_http_post_json_success(mock_http_request_primitive):
    """Verify the wrapper correctly calls http_request primitive with JSON payload."""
    payload_dict = {"key": "value", "id": 123}
    input_data = HttpPostJsonInput(
        url="http://api.test/submit", payload=payload_dict, timeout=20
    )

    result = http_post_json(input_data)

    mock_http_request_primitive.assert_called_once()
    call_arg_input = mock_http_request_primitive.call_args[0][0]

    assert isinstance(call_arg_input, HttpRequestInput)
    assert call_arg_input.method == "POST"
    assert call_arg_input.url == "http://api.test/submit"
    assert call_arg_input.headers is not None
    assert call_arg_input.headers.get("Content-Type") == "application/json"
    assert call_arg_input.json_payload == payload_dict


def test_upload_to_grafana_success(mock_http_request_primitive):
    """Verify the wrapper calls http_request primitive with correct headers for Grafana."""
    payload_dict = {"message": "deployment complete"}
    input_data = GrafanaUploadInput(
        url="http://grafana/api/annotations",
        payload=payload_dict,
        token="my-secret-token",
        timeout=20,
    )

    result = upload_to_grafana(input_data)

    mock_http_request_primitive.assert_called_once()
    call_arg_input = mock_http_request_primitive.call_args[0][0]

    assert isinstance(call_arg_input, HttpRequestInput)
    assert call_arg_input.headers is not None
    assert call_arg_input.headers.get("Authorization") == "Bearer my-secret-token"
