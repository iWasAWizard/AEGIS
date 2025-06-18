# aegis/tools/wrappers/browser/web_interact.py
"""
A tool for performing interactive actions on a webpage using Selenium.

This module provides a single, flexible tool for web automation, supporting
actions like navigating, clicking elements, typing text, and selecting
dropdown options in a headless browser.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

# Selenium imports no longer needed directly here for Options, By, Select, WebDriverWait, if executor handles more
from selenium import webdriver  # Still needed for type hint in action func
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

# from selenium.webdriver.firefox.options import Options # Handled by executor
# from selenium.common.exceptions import TimeoutException, WebDriverException # Handled by executor

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger
from aegis.exceptions import ToolExecutionError

# Import SeleniumExecutor
from aegis.executors.selenium import SeleniumExecutor

logger = setup_logger(__name__)


class WebInteractionInput(BaseModel):
    """Input model for interacting with a webpage.

    :ivar action: The action to perform: "navigate", "click", "type", "select", or "wait".
    :vartype action: Literal["navigate", "click", "type", "select", "wait"]
    :ivar url: URL to navigate to (required for 'navigate' action).
    :vartype url: Optional[str]
    :ivar selector: CSS selector for the target element.
    :vartype selector: Optional[str]
    :ivar value: Text to type or the value of the option to select.
    :vartype value: Optional[str]
    :ivar wait_timeout: Time in seconds to wait for elements to appear for interactions.
    :vartype wait_timeout: int
    :ivar browser: Name of the browser to use (default: firefox).
    :vartype browser: Optional[str]
    """

    action: Literal["navigate", "click", "type", "select", "wait"] = Field(
        ..., description="The action to perform."
    )
    url: Optional[str] = Field(
        None, description="URL to navigate to (required for 'navigate' action)."
    )
    selector: Optional[str] = Field(
        None, description="CSS selector for the target element."
    )
    value: Optional[str] = Field(
        None, description="Text to type or the value of the option to select."
    )
    wait_timeout: int = Field(  # This timeout is for element presence, not page load.
        10,
        gt=0,
        description="Time in seconds to wait for elements to appear for interactions.",
    )
    browser: Optional[str] = Field(
        "firefox", description="Browser to use (e.g., 'firefox')."
    )


@register_tool(
    name="web_interact",
    input_model=WebInteractionInput,
    description="Interacts with a webpage via SeleniumExecutor. Supports: navigate, click, type, wait, select.",
    tags=["browser", "selenium", "web", "automation", "wrapper"],
    category="wrapper",
    safe_mode=False,
)
def web_interact(input_data: WebInteractionInput) -> str:
    """Performs a single interaction on a webpage using SeleniumExecutor.

    :param input_data: An object containing the action and its parameters.
    :type input_data: WebInteractionInput
    :return: A string indicating the outcome of the action.
    :rtype: str
    :raises ToolExecutionError: If SeleniumExecutor encounters an error.
    """
    logger.info(
        f"Performing web action: '{input_data.action}' on selector: '{input_data.selector or input_data.url}' using {input_data.browser or 'firefox'}"
    )

    # For navigate, the implicit_wait of the executor handles load timing.
    # For other actions, input_data.wait_timeout is for explicit waits for elements.
    executor = SeleniumExecutor(
        browser_name=input_data.browser or "firefox",
        implicit_wait=input_data.wait_timeout,  # Using this as the general implicit wait for the session
    )

    def _interaction_logic(driver: webdriver.remote.webdriver.WebDriver) -> str:
        if input_data.action == "navigate":
            if not input_data.url:
                raise ToolExecutionError("URL must be provided for 'navigate' action.")
            driver.get(input_data.url)
            return f"Successfully navigated to {input_data.url}"

        if not input_data.selector:
            raise ToolExecutionError(
                f"CSS selector must be provided for '{input_data.action}' action."
            )

        # Explicit wait for element presence for interactable actions
        wait = WebDriverWait(driver, input_data.wait_timeout)
        element = wait.until(
            ec.presence_of_element_located((By.CSS_SELECTOR, input_data.selector))
        )

        if input_data.action == "click":
            element.click()
            return f"Clicked element with selector: '{input_data.selector}'"
        elif input_data.action == "type":
            if input_data.value is None:
                raise ToolExecutionError(
                    "A 'value' must be provided for 'type' action."
                )
            element.clear()
            element.send_keys(input_data.value)
            return f"Typed '{input_data.value}' into element: '{input_data.selector}'"
        elif input_data.action == "select":
            if input_data.value is None:
                raise ToolExecutionError(
                    "A 'value' must be provided for 'select' action."
                )
            select_element = Select(element)
            select_element.select_by_value(input_data.value)
            return f"Selected option with value '{input_data.value}' from dropdown: '{input_data.selector}'"
        elif input_data.action == "wait":
            return f"Element '{input_data.selector}' was successfully found and waited for."
        else:
            raise ToolExecutionError(
                f"Unknown web_interact action: {input_data.action}"
            )

    try:
        return executor.execute_action(_interaction_logic)
    # ToolExecutionError from SeleniumExecutor will propagate
    except ToolExecutionError:
        raise
    except Exception as e:  # Catch any other unexpected error in this tool's logic
        logger.exception(
            f"Unexpected error in web_interact tool logic for action {input_data.action}"
        )
        raise ToolExecutionError(f"Unexpected tool error in web_interact: {e}")
