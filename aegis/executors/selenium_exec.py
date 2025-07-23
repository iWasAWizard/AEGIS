# aegis/executors/selenium_exec.py
"""
Provides a client for performing Selenium-based browser operations.
"""
from pathlib import Path
from typing import Callable, Any, Optional, Dict

from selenium import webdriver

# from selenium.webdriver.chrome.options import Options as ChromeOptions # If Chrome support is added
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver  # For type hinting

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

SUPPORTED_BROWSERS = ["firefox"]  # Add "chrome" etc. if supported later


class SeleniumExecutor:
    """
    A client for managing Selenium WebDriver instances and performing browser operations.
    Ensures WebDriver is properly initialized and quit.
    """

    def __init__(
        self,
        browser_name: str = "firefox",
        headless: bool = True,
        page_load_timeout: int = 30,  # Default page load timeout
        implicit_wait: int = 10,  # Default implicit wait
    ):
        """
        Initializes the SeleniumExecutor.

        :param browser_name: Name of the browser to use (e.g., "firefox").
        :type browser_name: str
        :param headless: Whether to run the browser in headless mode.
        :type headless: bool
        :param page_load_timeout: Time in seconds to wait for a page to load.
        :type page_load_timeout: int
        :param implicit_wait: Time in seconds for implicit waits for elements.
        :type implicit_wait: int
        :raises ConfigurationError: If an unsupported browser is specified.
        """
        if browser_name.lower() not in SUPPORTED_BROWSERS:
            raise ToolExecutionError(
                f"Unsupported browser: {browser_name}. Supported: {SUPPORTED_BROWSERS}"
            )
        self.browser_name = browser_name.lower()
        self.headless = headless
        self.page_load_timeout = page_load_timeout
        self.implicit_wait = implicit_wait
        self.driver: Optional[WebDriver] = None  # For type hinting

    def _get_driver(self) -> WebDriver:
        """Initializes and returns a WebDriver instance."""
        if self.driver and self._is_driver_active():
            return self.driver

        logger.debug(
            f"Initializing {self.browser_name} WebDriver (headless={self.headless})..."
        )
        try:
            if self.browser_name == "firefox":
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")
                # Ensure geckodriver is in PATH or specify its path:
                # service = webdriver.FirefoxService(executable_path="/path/to/geckodriver")
                # self.driver = webdriver.Firefox(options=options, service=service)
                self.driver = webdriver.Firefox(options=options)
            # Add other browsers like Chrome here if needed
            # elif self.browser_name == "chrome":
            #     options = ChromeOptions()
            #     if self.headless:
            #         options.add_argument("--headless")
            #         options.add_argument("--disable-gpu") # Often needed for headless chrome
            #     self.driver = webdriver.Chrome(options=options)
            else:
                # This case should be caught by __init__, but defensive check
                raise ToolExecutionError(
                    f"Attempted to initialize unsupported browser: {self.browser_name}"
                )

            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(self.implicit_wait)  # Global implicit wait
            logger.info(
                f"{self.browser_name.capitalize()} WebDriver initialized successfully."
            )
            return self.driver
        except WebDriverException as e:
            logger.error(f"Failed to initialize {self.browser_name} WebDriver: {e.msg}")
            raise ToolExecutionError(
                f"WebDriver initialization failed for {self.browser_name}: {e.msg}"
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error initializing WebDriver for {self.browser_name}"
            )
            raise ToolExecutionError(f"Unexpected error initializing WebDriver: {e}")

    def _is_driver_active(self) -> bool:
        """Checks if the driver session is still active."""
        if not self.driver:
            return False
        try:
            # A lightweight command to check session validity
            _ = self.driver.current_url
            return True
        except WebDriverException:
            return False

    def execute_action(self, action_func: Callable[[WebDriver], Any]) -> Any:
        """
        Executes a given function that takes a WebDriver instance as an argument.
        Manages the WebDriver lifecycle (setup and teardown).

        :param action_func: A callable that performs browser actions using the WebDriver.
                            It should take one argument: the WebDriver instance.
        :type action_func: Callable[[WebDriver], Any]
        :return: The result of the action_func.
        :rtype: Any
        :raises ToolExecutionError: If any WebDriver or other exception occurs during action.
        """
        driver = None
        try:
            driver = self._get_driver()
            result = action_func(driver)
            return result
        except (
            WebDriverException,
            TimeoutException,
        ) as e:  # Catch common Selenium exceptions
            # Attempt to get current URL for better error context, if driver is available
            current_url_msg = "N/A"
            if driver and self._is_driver_active():
                try:
                    current_url_msg = driver.current_url
                except WebDriverException:
                    pass  # Driver might have crashed, current_url fails

            error_detail = e.msg if hasattr(e, "msg") else str(e)
            logger.error(
                f"Selenium action failed on URL '{current_url_msg}': {error_detail}"
            )
            raise ToolExecutionError(
                f"Selenium action failed (URL: {current_url_msg}): {error_detail}"
            )
        except (
            ToolExecutionError
        ):  # Re-raise specific ToolExecutionErrors from action_func
            raise
        except Exception as e:
            logger.exception(
                "An unexpected error occurred during Selenium action execution."
            )
            raise ToolExecutionError(f"Unexpected error during Selenium action: {e}")
        finally:
            self._quit_driver()

    def _quit_driver(self):
        """Quits the WebDriver if it's active."""
        if self.driver:
            logger.debug("Quitting WebDriver...")
            try:
                self.driver.quit()
                logger.info("WebDriver quit successfully.")
            except Exception as e:
                logger.error(f"Error quitting WebDriver: {e}")
            finally:
                self.driver = None

    # --- Convenience methods for common actions ---
    # These can be called by tools if preferred over passing a lambda to execute_action

    def get_page_details(self, url: str) -> Dict[str, Any]:
        """Navigates to a URL and returns page title, current URL, text, and HTML source."""

        def _action(driver: WebDriver) -> Dict[str, Any]:
            driver.get(url)
            # implicit_wait in _get_driver should handle general load timing
            title = driver.title
            current_url = driver.current_url
            try:
                body = driver.find_element(webdriver.common.by.By.TAG_NAME, "body")
                text = body.text.strip()
            except WebDriverException:  # Body might not be found on some error pages
                text = ""
                logger.warning(
                    f"Could not find <body> tag on {url}, text will be empty."
                )

            html = driver.page_source.strip()
            return {
                "title": title,
                "current_url": current_url,
                "text": text,
                "html": html,
            }

        return self.execute_action(_action)

    def take_screenshot(self, url: str, save_path: str) -> str:
        """Navigates to a URL and saves a screenshot."""

        def _action(driver: WebDriver) -> str:
            driver.get(url)
            # Ensure screenshot directory exists just before saving
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            driver.save_screenshot(save_path)
            return f"Screenshot saved to {save_path}"

        return self.execute_action(_action)
