# aegis/executors/selenium_exec.py
"""
Provides a client for Selenium-based web automation.
"""
from typing import Optional, Dict, Any

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time

logger = setup_logger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import (
        WebDriverException,
        TimeoutException,
        NoSuchElementException,
    )

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class SeleniumExecutor:
    """A client for simple Selenium actions with ephemeral drivers."""

    def __init__(
        self,
        headless: bool = True,
        driver_path: Optional[str] = None,
        implicit_wait_s: int = 5,
    ):
        """
        :param headless: Run Chrome in headless mode.
        :type headless: bool
        :param driver_path: Optional path to a chromedriver or compatible driver.
        :type driver_path: Optional[str]
        :param implicit_wait_s: Implicit wait time in seconds.
        :type implicit_wait_s: int
        """
        if not SELENIUM_AVAILABLE:
            raise ToolExecutionError("Selenium is not installed.")
        self.headless = headless
        self.driver_path = driver_path
        self.implicit_wait_s = implicit_wait_s
        self._driver: Optional[webdriver.Chrome] = None

    def _get_driver(self) -> webdriver.Chrome:
        """
        Lazily create a Chrome driver with reasonable defaults.
        """
        if self._driver is not None:
            return self._driver

        options = ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        try:
            if self.driver_path:
                driver = webdriver.Chrome(self.driver_path, options=options)
            else:
                driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(self.implicit_wait_s)
            self._driver = driver
            return driver
        except WebDriverException as e:
            raise ToolExecutionError(f"Failed to start Chrome driver: {e}") from e

    def _is_driver_active(self) -> bool:
        return self._driver is not None

    def execute_action(
        self,
        action: str,
        url: str,
        selector: str | None = None,
        text: str | None = None,
        screenshot_path: str | None = None,
    ) -> Dict[str, Any]:
        """
        Perform a simple action: 'goto', 'click', 'type', 'screenshot'.
        """
        try:
            driver = self._get_driver()
            if action == "goto":
                driver.get(url)
                return {"ok": True, "title": driver.title}
            elif action == "click":
                if not selector:
                    raise ToolExecutionError("selector is required for click")
                el = driver.find_element(By.CSS_SELECTOR, selector)
                el.click()
                return {"ok": True}
            elif action == "type":
                if not selector or text is None:
                    raise ToolExecutionError("selector and text are required for type")
                el = driver.find_element(By.CSS_SELECTOR, selector)
                el.clear()
                el.send_keys(text)
                return {"ok": True}
            elif action == "screenshot":
                if not screenshot_path:
                    raise ToolExecutionError(
                        "screenshot_path is required for screenshot"
                    )
                driver.save_screenshot(screenshot_path)
                return {"ok": True, "path": screenshot_path}
            else:
                raise ToolExecutionError(f"Unsupported action: {action}")
        except (NoSuchElementException, TimeoutException, WebDriverException) as e:
            raise ToolExecutionError(f"Selenium action error: {e}") from e

    def _quit_driver(self) -> None:
        try:
            if self._driver is not None:
                self._driver.quit()
                self._driver = None
        except Exception:
            self._driver = None

    def get_page_details(self, url: str, selector: str | None = None) -> Dict[str, Any]:
        """
        Navigate to a page and optionally return text of an element.
        """
        try:
            driver = self._get_driver()
            driver.get(url)
            title = driver.title
            details: Dict[str, Any] = {"title": title}
            if selector:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, selector)
                    details["text"] = el.text
                except NoSuchElementException:
                    details["text"] = None
            return details
        except (TimeoutException, WebDriverException) as e:
            raise ToolExecutionError(f"Selenium navigation error: {e}") from e

    def take_screenshot(self, url: str, path: str) -> bool:
        """
        Navigate to a page and take a screenshot to the given path.
        """
        try:
            driver = self._get_driver()
            driver.get(url)
            return bool(driver.save_screenshot(path))
        except (TimeoutException, WebDriverException) as e:
            raise ToolExecutionError(f"Selenium screenshot error: {e}") from e
        finally:
            self._quit_driver()


# === ToolResult wrappers ===
def _now_ms() -> int:
    return int(time.time() * 1000)


def _error_type_from_exception(e: Exception) -> str:
    msg = str(e).lower()
    if "timeout" in msg:
        return "Timeout"
    if "permission" in msg or "auth" in msg:
        return "Auth"
    if "not found" in msg or "no such" in msg:
        return "NotFound"
    if "parse" in msg or "json" in msg:
        return "Parse"
    return "Runtime"


class SeleniumExecutorToolResultMixin:
    def execute_action_result(
        self,
        action: str,
        url: str,
        selector: str | None = None,
        text: str | None = None,
        screenshot_path: str | None = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="selenium.execute_action",
                args=redact_for_log(
                    {"action": action, "url": url, "selector": selector}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] selenium.execute_action",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.execute_action(
                action=action,
                url=url,
                selector=selector,
                text=text,
                screenshot_path=screenshot_path,
            )
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"action": action, "url": url},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"action": action, "url": url},
            )

    def get_page_details_result(
        self, url: str, selector: str | None = None
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="selenium.get_page_details",
                args=redact_for_log({"url": url, "selector": selector}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] selenium.get_page_details",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.get_page_details(url=url, selector=selector)
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"url": url, "selector": selector},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"url": url, "selector": selector},
            )

    def take_screenshot_result(self, url: str, path: str) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="selenium.screenshot",
                args=redact_for_log({"url": url, "path": path}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] selenium.screenshot",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.take_screenshot(url=url, path=path)
            return ToolResult.ok_result(
                stdout=str(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"url": url, "path": path},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"url": url, "path": path},
            )


SeleniumExecutor.execute_action_result = (
    SeleniumExecutorToolResultMixin.execute_action_result
)
SeleniumExecutor.get_page_details_result = (
    SeleniumExecutorToolResultMixin.get_page_details_result
)
SeleniumExecutor.take_screenshot_result = (
    SeleniumExecutorToolResultMixin.take_screenshot_result
)
