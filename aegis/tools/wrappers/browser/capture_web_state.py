"""
Tool to capture a webpage's state with screenshot, text, and DOM snapshot.
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
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)
SCREENSHOT_DIR = Path("reports/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class CaptureWebStateInput(BaseModel):
    """
    CaptureWebStateInput class.
    """

    url: str = Field(..., description="URL of the page to capture")
    wait_seconds: int = Field(..., description="Seconds to wait before capturing DOM")


@register_tool(
    name="capture_web_state",
    input_model=CaptureWebStateInput,
    description="Captures a web page's title, URL, text, DOM, and screenshot.",
    tags=["browser", "introspection", "selenium"],
    category="wrapper",
    safe_mode=False,
)
def capture_web_state(input_data: CaptureWebStateInput) -> str:
    """
    capture_web_state.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"[capture_web_state] Capturing from: {input_data.url}")
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
            logger.info(f"[capture_web_state] Screenshot saved: {screenshot_path}")
            return f"📄 Title: {title}\n🔗 URL: {current_url}\n🧾 Text: {text[:500]}...\n" \
                   f"📦 HTML: {html[:500]}...\n🖼 Screenshot saved to: {screenshot_path}"
    except WebDriverException as e:
        logger.error(f"[capture_web_state] WebDriver error: {e}")
        return f"Selenium WebDriver error: {e}"
    except Exception as e:
        logger.exception(f"[capture_web_state] Unexpected error: {e}")
        return f"Unhandled exception: {e}"
