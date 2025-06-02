"""
Selenium tool for headless web automation using Firefox.
Supports navigation, click, type, wait, and select actions.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class WebInteractionInput(BaseModel):
    """
    Represents the WebInteractionInput class.

    Encapsulates all necessary parameters for interacting with a web page, such as actions, selectors, and payloads.
    """

    action: Literal["navigate", "click", "type", "select", "wait"]
    url: Optional[str] = Field(..., description="URL to navigate to.")
    selector: Optional[str] = Field(
        ..., description="CSS selector for the target element."
    )
    value: Optional[str] = Field(..., description="Text to type or value to select.")
    wait_timeout: int = Field(..., description="Time to wait for elements to appear.")


@register_tool(
    name="web_interact",
    input_model=WebInteractionInput,
    description="Interact with a webpage via headless Firefox. Supports navigate, click, type, wait, select.",
    tags=["browser", "automation", "selenium"],
    category="wrapper",
    safe_mode=False,
)
def web_interact(input_data: WebInteractionInput) -> str:
    """
    web_interact.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(
        f"[web_interact] Action: {input_data.action},"
        f"                 Selector: {input_data.selector},"
        f"                 Value: {input_data.value}"
    )
    options = Options()
    options.headless = True
    try:
        with webdriver.Firefox(options=options) as driver:
            driver.set_page_load_timeout(input_data.wait_timeout)
            if input_data.action == "navigate":
                if not input_data.url:
                    return "Missing URL for navigation."
                driver.get(input_data.url)
                return f"Navigated to {input_data.url}"
            if input_data.action in {"click", "type", "select", "wait"}:
                if not input_data.selector:
                    return "Missing selector for interaction."
                WebDriverWait(driver, input_data.wait_timeout).until(
                    ec.presence_of_element_located(
                        (By.CSS_SELECTOR, input_data.selector)
                    )
                )
                element = driver.find_element(By.CSS_SELECTOR, input_data.selector)
                if input_data.action == "click":
                    element.click()
                    return f"Clicked element: {input_data.selector}"
                if input_data.action == "type":
                    if input_data.value is None:
                        return "Missing value for typing."
                    element.clear()
                    element.send_keys(input_data.value)
                    return f"Typed into element: {input_data.selector}"
                if input_data.action == "select":
                    if input_data.value is None:
                        return "Missing value for selection."
                    select = Select(element)
                    select.select_by_value(input_data.value)
                    return f"Selected '{input_data.value}' from dropdown."
                if input_data.action == "wait":
                    return f"Element {input_data.selector} appeared on page."
    except TimeoutException as e:
        logger.warning(f"[web_interact] Timeout: {e}")
        return f"Timeout while performing '{input_data.action}' on {input_data.selector or input_data.url}"
    except WebDriverException as e:
        logger.error(f"[web_interact] WebDriver failure: {e}")
        return f"Selenium error: {e}"
    except Exception as e:
        logger.exception(f"[web_interact] Unexpected error: {e}")
        return f"Unhandled exception: {e}"
