# aegis/tools/wrappers/browser/web_interact.py
"""
A tool for performing interactive actions on a webpage using Selenium.

This module provides a single, flexible tool for web automation, supporting
actions like navigating, clicking elements, typing text, and selecting
dropdown options in a headless browser.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

# Import ToolExecutionError
from aegis.exceptions import ToolExecutionError

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
    :ivar wait_timeout: Time in seconds to wait for elements to appear.
    :vartype wait_timeout: int
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
    wait_timeout: int = Field(
        10, description="Time in seconds to wait for elements to appear."
    )


@register_tool(
    name="web_interact",
    input_model=WebInteractionInput,
    description="Interacts with a webpage via headless Firefox. Supports: navigate, click, type, wait, select.",
    tags=["browser", "selenium", "web", "automation", "wrapper"],
    category="wrapper",
    safe_mode=False,
)
def web_interact(input_data: WebInteractionInput) -> str:
    """Performs a single interaction on a webpage using a headless Firefox browser.

    This tool acts as a versatile interface for web automation. It can perform
    one of several actions in a single call, such as navigating to a page,
    clicking a button, or typing into a form field. It uses explicit waits
    to ensure elements are present before interacting with them, making it more
    resilient to variations in page load times.

    :param input_data: An object containing the action and its parameters.
    :type input_data: WebInteractionInput
    :return: A string indicating the outcome of the action.
    :rtype: str
    :raises ToolExecutionError: If Selenium WebDriver encounters an error or any other exception occurs.
    """
    logger.info(
        f"Performing web action: '{input_data.action}' on selector: '{input_data.selector or input_data.url}'"
    )
    options = Options()
    options.add_argument("--headless")

    driver = None
    try:
        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(input_data.wait_timeout)

        if input_data.action == "navigate":
            if not input_data.url:
                raise ToolExecutionError("URL must be provided for 'navigate' action.")
            driver.get(input_data.url)
            return f"Successfully navigated to {input_data.url}"

        # All other actions require a selector
        if not input_data.selector:
            raise ToolExecutionError(
                f"CSS selector must be provided for '{input_data.action}' action."
            )

        # Explicitly wait for the element to be present before interacting.
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
            # This case should ideally not be reached if Pydantic validation of 'action' is exhaustive.
            raise ToolExecutionError(
                f"Unknown web_interact action: {input_data.action}"
            )

    except TimeoutException:
        current_url_msg = driver.current_url if driver else "N/A"
        error_msg = f"Timeout waiting for element '{input_data.selector}' on URL '{current_url_msg}' after {input_data.wait_timeout}s."
        logger.warning(error_msg)
        raise ToolExecutionError(error_msg)
    except WebDriverException as e:  # Catch specific Selenium errors
        logger.error(f"WebDriver action '{input_data.action}' failed: {e.msg}")
        raise ToolExecutionError(f"Selenium WebDriver error: {e.msg}")
    except ToolExecutionError:  # Re-raise ToolExecutionErrors from our checks
        raise
    except Exception as e:  # Catch any other unexpected errors
        logger.exception("An unexpected error occurred during web interaction.")
        raise ToolExecutionError(
            f"An unhandled exception occurred during web interaction: {e}"
        )
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error quitting WebDriver: {e}")

    # This line should not be reached if all paths return or raise. Added for safety.
    raise ToolExecutionError(
        "Unknown web_interact action specified or action failed to return a result."
    )
