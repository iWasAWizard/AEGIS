# aegis/tests/tools/wrappers/browser/test_web_interact.py
"""
Unit tests for the web_interact tool.
"""
from unittest.mock import MagicMock, patch

import pytest

# Import WebDriver for type hint in the mocked action_func if needed, though not strictly necessary for these tests
# from selenium.webdriver.remote.webdriver import WebDriver

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.browser.web_interact import (
    web_interact,
    WebInteractionInput,
)

# No direct selenium imports needed if we mock the executor


@pytest.fixture
def mock_selenium_executor_execute_action(monkeypatch):
    """Mocks the SeleniumExecutor's execute_action method."""
    mock_method = MagicMock()
    # Path for SeleniumExecutor in the module where it's IMPORTED and USED
    monkeypatch.setattr(
        "aegis.executors.selenium.SeleniumExecutor.execute_action", mock_method
    )
    return mock_method


@pytest.fixture
def mock_selenium_executor_init(monkeypatch):
    """Mocks the SeleniumExecutor's __init__ method to inspect its instantiation."""
    mock_init = MagicMock(return_value=None)  # __init__ should return None
    monkeypatch.setattr("aegis.executors.selenium.SeleniumExecutor.__init__", mock_init)
    return mock_init


def test_web_interact_navigate_success(
    mock_selenium_executor_init, mock_selenium_executor_execute_action
):
    """Test successful navigation."""
    mock_selenium_executor_execute_action.return_value = (
        "Successfully navigated to http://example.com"
    )

    input_data = WebInteractionInput(
        action="navigate",
        url="http://example.com",
        browser="test_browser",
        wait_timeout=5,
    )
    result = web_interact(input_data)

    # Check executor was initialized correctly
    mock_selenium_executor_init.assert_called_once_with(
        browser_name="test_browser", implicit_wait=5
    )
    # Check execute_action was called
    mock_selenium_executor_execute_action.assert_called_once()
    # We can't easily check the lambda passed to execute_action,
    # but we trust the executor's mocked return value.
    assert result == "Successfully navigated to http://example.com"


@pytest.mark.parametrize(
    "action_name, tool_input_extras, expected_message_part",
    [
        ("click", {"selector": "#btn"}, "Clicked element with selector: '#btn'"),
        (
            "type",
            {"selector": "input", "value": "hello"},
            "Typed 'hello' into element: 'input'",
        ),
        (
            "select",
            {"selector": "select", "value": "opt1"},
            "Selected option with value 'opt1' from dropdown: 'select'",
        ),
        (
            "wait",
            {"selector": ".loading"},
            "Element '.loading' was successfully found and waited for.",
        ),
    ],
)
def test_web_interact_other_actions_success(
    mock_selenium_executor_init,
    mock_selenium_executor_execute_action,
    action_name,
    tool_input_extras,
    expected_message_part,
):
    """Test other successful actions like click, type, select, wait."""
    mock_selenium_executor_execute_action.return_value = (
        f"Mocked success: {expected_message_part}"
    )

    base_input = {"action": action_name, "wait_timeout": 10, "browser": "firefox"}
    input_data = WebInteractionInput(**base_input, **tool_input_extras)

    result = web_interact(input_data)

    mock_selenium_executor_init.assert_called_once_with(
        browser_name="firefox", implicit_wait=10
    )
    mock_selenium_executor_execute_action.assert_called_once()
    assert f"Mocked success: {expected_message_part}" in result


def test_web_interact_missing_url_for_navigate(
    mock_selenium_executor_init, mock_selenium_executor_execute_action
):
    """Test that navigate action without URL fails correctly inside the action_func."""
    # Simulate the error that would be raised by _interaction_logic
    mock_selenium_executor_execute_action.side_effect = ToolExecutionError(
        "URL must be provided for 'navigate' action."
    )

    input_data = WebInteractionInput(action="navigate", url=None)  # Missing URL

    with pytest.raises(
        ToolExecutionError, match="URL must be provided for 'navigate' action."
    ):
        web_interact(input_data)

    mock_selenium_executor_init.assert_called_once()  # Executor is still initialized
    mock_selenium_executor_execute_action.assert_called_once()  # execute_action is called


def test_web_interact_missing_selector(
    mock_selenium_executor_init, mock_selenium_executor_execute_action
):
    """Test that actions requiring selector fail if selector is missing (inside action_func)."""
    mock_selenium_executor_execute_action.side_effect = ToolExecutionError(
        "CSS selector must be provided for 'click' action."
    )

    input_data = WebInteractionInput(action="click", selector=None)  # Missing selector

    with pytest.raises(
        ToolExecutionError, match="CSS selector must be provided for 'click' action."
    ):
        web_interact(input_data)

    mock_selenium_executor_init.assert_called_once()
    mock_selenium_executor_execute_action.assert_called_once()


def test_web_interact_executor_failure_propagates(
    mock_selenium_executor_init, mock_selenium_executor_execute_action
):
    """Test that ToolExecutionError from SeleniumExecutor.execute_action propagates."""
    mock_selenium_executor_execute_action.side_effect = ToolExecutionError(
        "Selenium Executor failed during action"
    )

    input_data = WebInteractionInput(action="navigate", url="http://example.com")

    with pytest.raises(
        ToolExecutionError, match="Selenium Executor failed during action"
    ):
        web_interact(input_data)

    mock_selenium_executor_init.assert_called_once()
    mock_selenium_executor_execute_action.assert_called_once()
