# aegis/tools/wrappers/browser/capture_web_state.py
"""
A tool to capture the state of a webpage using Selenium.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.webdriver.common.by import By

from aegis.exceptions import ToolExecutionError
from aegis.executors.selenium import SeleniumExecutor
from aegis.registry import register_tool
from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

config = get_config()
SCREENSHOT_DIR = Path(config.get("paths", {}).get("screenshots", "reports/screenshots"))
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class CaptureWebStateInput(BaseModel):
    """Input model for capturing the state of a webpage.

    :ivar url: The full URL of the webpage to capture.
    :vartype url: str
    :ivar wait_seconds: Seconds to wait for the page to implicitly load elements before capturing.
    :vartype wait_seconds: int
    :ivar browser: Name of the browser to use (default: firefox).
    :vartype browser: Optional[str]
    """

    url: str = Field(..., description="The full URL of the webpage to capture.")
    wait_seconds: int = Field(
        10, gt=0, description="Seconds for implicit wait for page elements."
    )
    browser: Optional[str] = Field(
        "firefox", description="Browser to use (e.g., 'firefox')."
    )


@register_tool(
    name="capture_web_state",
    input_model=CaptureWebStateInput,
    description="Captures a web page's title, URL, text, DOM, and a screenshot using SeleniumExecutor.",
    tags=["browser", "selenium", "web", "wrapper"],
    category="wrapper",
    safe_mode=False,
    purpose="Get a comprehensive snapshot of a webpage's state.",
)
def capture_web_state(input_data: CaptureWebStateInput) -> str:
    """Uses SeleniumExecutor to navigate to a URL and capture its state including a screenshot.

    :param input_data: An object containing the URL, wait time, and browser.
    :type input_data: CaptureWebStateInput
    :return: A formatted string summarizing the captured state and screenshot path.
    :rtype: str
    :raises ToolExecutionError: If SeleniumExecutor encounters an error.
    """
    logger.info(
        f"Capturing web state from: {input_data.url} using {input_data.browser or 'firefox'}"
    )

    executor = SeleniumExecutor(
        browser_name=input_data.browser or "firefox",
        implicit_wait=input_data.wait_seconds,  # Pass wait_seconds as implicit_wait
    )

    try:
        # Get page details (title, url, text, html)
        page_details = executor.get_page_details(input_data.url)

        # Take screenshot
        snapshot_id = (
            f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        )
        screenshot_path = SCREENSHOT_DIR / f"{snapshot_id}.png"

        # The take_screenshot method in executor handles navigation again, which is redundant here.
        # We can either:
        # 1. Modify executor to have a method that takes screenshot of current page.
        # 2. Call driver.save_screenshot directly within a custom action_func.
        # Let's use option 2 for now for simplicity, then consider enhancing executor.

        def _capture_action(
            driver: webdriver,
        ) -> tuple[dict, str]:
            driver.get(input_data.url)  # Navigate first
            title = driver.title
            current_url = driver.current_url
            body = driver.find_element(webdriver.common.by.By.TAG_NAME, "body")
            text = body.text.strip()
            html = driver.page_source.strip()

            _screenshot_path = SCREENSHOT_DIR / f"{snapshot_id}.png"
            _screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            driver.save_screenshot(str(_screenshot_path))
            logger.info(f"Screenshot saved to: {_screenshot_path}")

            details = {
                "title": title,
                "current_url": current_url,
                "text": text,
                "html": html,
            }
            return details, str(_screenshot_path)

        page_details_dict, actual_screenshot_path_str = executor.execute_action(
            _capture_action
        )

        return (
            f"Title: {page_details_dict['title']}\n"
            f"URL: {page_details_dict['current_url']}\n"
            f"Text (first 500 chars): {page_details_dict['text'][:500]}...\n"
            f"HTML (first 500 chars): {page_details_dict['html'][:500]}...\n"
            f"Screenshot saved to: {actual_screenshot_path_str}"
        )
    # ToolExecutionError from SeleniumExecutor will propagate
    except ToolExecutionError:
        raise
    except Exception as e:  # Catch any other unexpected error in this tool's logic
        logger.exception(
            f"Unexpected error in capture_web_state tool logic for {input_data.url}"
        )
        raise ToolExecutionError(f"Unexpected tool error in capture_web_state: {e}")
