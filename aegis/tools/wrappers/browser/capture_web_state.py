# aegis/tools/wrappers/browser/capture_web_state.py
"""
A tool to capture the state of a webpage using Selenium.
"""
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

from aegis.registry import register_tool
from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# Load the screenshot directory from the central config.
config = get_config()
SCREENSHOT_DIR = Path(config.get("paths", {}).get("screenshots", "reports/screenshots"))
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class CaptureWebStateInput(BaseModel):
    """Input model for capturing the state of a webpage."""

    url: str = Field(..., description="The full URL of the webpage to capture.")
    wait_seconds: int = Field(
        10, description="Seconds to wait for the page to load before capturing."
    )


@register_tool(
    name="capture_web_state",
    input_model=CaptureWebStateInput,
    description="Captures a web page's title, URL, text, DOM, and a screenshot.",
    tags=["browser", "selenium", "web", "wrapper"],
    category="wrapper",
    safe_mode=False,
    purpose="Get a comprehensive snapshot of a webpage's state.",
)
def capture_web_state(input_data: CaptureWebStateInput) -> str:
    """Uses a headless Firefox browser to navigate to a URL and capture its state.

    :param input_data: An object containing the URL and wait time.
    :type input_data: CaptureWebStateInput
    :return: A formatted string summarizing the captured state and screenshot path.
    :rtype: str
    """
    logger.info(f"Capturing web state from: {input_data.url}")
    options = Options()
    options.headless = True

    try:
        with webdriver.Firefox(options=options) as driver:
            driver.get(input_data.url)
            driver.implicitly_wait(input_data.wait_seconds)

            title = driver.title
            current_url = driver.current_url
            body = driver.find_element(By.TAG_NAME, "body")
            text = body.text.strip()
            html = driver.page_source.strip()

            snapshot_id = (
                f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            )
            screenshot_path = SCREENSHOT_DIR / f"{snapshot_id}.png"
            driver.save_screenshot(str(screenshot_path))

            logger.info(f"Screenshot saved to: {screenshot_path}")

            return (
                f"Title: {title}\n"
                f"URL: {current_url}\n"
                f"Text (first 500 chars): {text[:500]}...\n"
                f"HTML (first 500 chars): {html[:500]}...\n"
                f"Screenshot saved to: {screenshot_path}"
            )
    except WebDriverException as e:
        logger.error(f"WebDriver error while capturing {input_data.url}: {e.msg}")
        return f"[ERROR] Selenium WebDriver error: {e.msg}"
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred while capturing {input_data.url}"
        )
        return f"[ERROR] An unhandled exception occurred: {e}"
