# aegis/tests/tools/wrappers/browser/test_capture_web_state.py
"""
Unit tests for the capture_web_state tool.
"""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.browser.capture_web_state import (
    capture_web_state,
    CaptureWebStateInput,
    SCREENSHOT_DIR,  # For verifying path
)


# SeleniumExecutor will be mocked, so selenium import isn't strictly needed here for tests
# but good for indicating context.
# pytest.importorskip("selenium", reason="selenium not available for testing.")


@pytest.fixture
def mock_selenium_executor(monkeypatch):
    """Mocks the SeleniumExecutor class and its execute_action method."""
    mock_execute_action = MagicMock()

    # Path for SeleniumExecutor in the module where it's IMPORTED and USED
    monkeypatch.setattr(
        "aegis.executors.selenium.SeleniumExecutor.execute_action", mock_execute_action
    )
    return mock_execute_action


@pytest.fixture
def mock_uuid_and_datetime(monkeypatch):
    """Mocks uuid.uuid4 and datetime.utcnow for predictable filenames."""
    mock_uuid = MagicMock()
    mock_uuid.hex = "abcdef"
    monkeypatch.setattr(uuid, "uuid4", MagicMock(return_value=mock_uuid))

    mock_dt = MagicMock(spec=datetime)
    mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
    monkeypatch.setattr(
        "aegis.tools.wrappers.browser.capture_web_state.datetime", mock_dt
    )


def test_capture_web_state_success(mock_selenium_executor, mock_uuid_and_datetime):
    """Verify the tool calls SeleniumExecutor.execute_action and formats the result."""

    # Define what the mocked _capture_action (passed to execute_action) would return
    mock_page_details = {
        "title": "Test Page",
        "current_url": "http://example.com",
        "text": "Page content here " * 100,  # Make it long enough for truncation
        "html": "<html><body>Page content here...</body></html>" * 20,
    }
    expected_screenshot_filename = "20240101_120000_abcdef.png"
    expected_screenshot_path_str = str(SCREENSHOT_DIR / expected_screenshot_filename)

    mock_selenium_executor.return_value = (
        mock_page_details,
        expected_screenshot_path_str,
    )

    input_data = CaptureWebStateInput(
        url="http://example.com", wait_seconds=5, browser="firefox"
    )
    result = capture_web_state(input_data)

    mock_selenium_executor.assert_called_once()
    # We can't easily inspect the lambda passed to execute_action directly,
    # but we can check that the SeleniumExecutor was instantiated correctly (implicitly by patching its method)
    # and that the result processing is correct.

    assert "Title: Test Page" in result
    assert "URL: http://example.com" in result
    assert f"Text (first 500 chars): {mock_page_details['text'][:500]}..." in result
    assert f"HTML (first 500 chars): {mock_page_details['html'][:500]}..." in result
    assert f"Screenshot saved to: {expected_screenshot_path_str}" in result


def test_capture_web_state_executor_failure(mock_selenium_executor):
    """Verify ToolExecutionError from SeleniumExecutor propagates."""
    mock_selenium_executor.side_effect = ToolExecutionError("Selenium failed hard")

    input_data = CaptureWebStateInput(url="http://example.com/fail", wait_seconds=5)

    with pytest.raises(ToolExecutionError, match="Selenium failed hard"):
        capture_web_state(input_data)
    mock_selenium_executor.assert_called_once()


@patch(
    "aegis.executors.selenium.SeleniumExecutor.__init__", return_value=None
)  # Mock init
def test_capture_web_state_browser_param_passed(
    mock_executor_init, mock_selenium_executor
):
    """Test that the browser parameter is passed to SeleniumExecutor."""
    mock_selenium_executor.return_value = ({"title": ""}, "path.png")  # Dummy return

    input_data = CaptureWebStateInput(
        url="http://example.com", wait_seconds=5, browser="chrome_test"
    )
    capture_web_state(input_data)

    # Check that SeleniumExecutor was initialized with the correct browser name
    mock_executor_init.assert_called_with(browser_name="chrome_test", implicit_wait=5)
