# aegis/tools/wrappers/gui.py
"""
Wrapper tools for controlling the Graphical User Interface (GUI) via pyautogui.

These tools allow the agent to perform actions like moving the mouse, clicking,
typing, and taking screenshots, enabling automation of desktop applications.
These tools require a graphical environment (an active desktop session) to run.
"""
import time
from typing import Literal, Optional, Tuple

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except (ImportError, Exception):
    # This can fail if there is no display (e.g., in a headless server)
    PYAUTOGUI_AVAILABLE = False

logger = setup_logger(__name__)


# --- Input Models ---


class GuiActionInput(BaseModel):
    """Input model for performing a basic GUI action.

    :ivar action: The action to perform: "move", "click", "double_click", "type", "screenshot".
    :vartype action: Literal["move", "click", "double_click", "type", "screenshot"]
    :ivar coordinates: The (x, y) screen coordinates for mouse actions.
    :vartype coordinates: Optional[Tuple[int, int]]
    :ivar text_to_type: The text to type for the 'type' action.
    :vartype text_to_type: Optional[str]
    :ivar screenshot_path: The local file path to save a screenshot.
    :vartype screenshot_path: Optional[str]
    :ivar duration_seconds: The time in seconds to perform a mouse move.
    :vartype duration_seconds: float
    """

    action: Literal["move", "click", "double_click", "type", "screenshot"] = Field(
        ..., description="The GUI action to perform."
    )
    coordinates: Optional[Tuple[int, int]] = Field(
        None, description="The (x, y) coordinates for mouse actions."
    )
    text_to_type: Optional[str] = Field(
        None, description="The text to type for the 'type' action."
    )
    screenshot_path: Optional[str] = Field(
        None, description="The local file path where the screenshot will be saved."
    )
    duration_seconds: float = Field(
        0.5, description="The time in seconds over which to perform a mouse move."
    )


class GuiFindAndClickInput(BaseModel):
    """Input model for finding an image on screen and interacting with it.

    :ivar template_image_path: The file path to the small image to find on the screen.
    :vartype template_image_path: str
    :ivar action: The mouse action to perform on the found image.
    :vartype action: Literal["click", "double_click", "move_to"]
    :ivar confidence: The confidence level for image matching (e.g., 0.9 for 90%).
    :vartype confidence: float
    :ivar timeout_seconds: How many seconds to wait for the image to appear on screen.
    :vartype timeout_seconds: int
    """

    template_image_path: str = Field(
        ..., description="The file path to the small image to find on the screen."
    )
    action: Literal["click", "double_click", "move_to"] = Field(
        "click", description="The mouse action to perform on the image."
    )
    confidence: float = Field(
        0.9,
        ge=0.1,
        le=1.0,
        description="The confidence level for image matching (e.g., 0.9 for 90%).",
    )
    timeout_seconds: int = Field(
        10, description="How many seconds to wait for the image to appear on screen."
    )


# --- Tools ---


@register_tool(
    name="gui_action",
    input_model=GuiActionInput,
    description="Performs a basic GUI action like moving the mouse, clicking, typing, or taking a screenshot.",
    tags=["gui", "pyautogui", "automation"],
    category="desktop",
    safe_mode=False,
    purpose="Perform a low-level GUI interaction.",
)
def gui_action(input_data: GuiActionInput) -> str:
    """A dispatcher for fundamental pyautogui actions.

    :param input_data: An object specifying the action and its required parameters.
    :type input_data: GuiActionInput
    :return: A string confirming the action's success or an error message.
    :rtype: str
    :raises ToolExecutionError: If pyautogui is unavailable, a GUI cannot be accessed, or required args are missing.
    """
    if not PYAUTOGUI_AVAILABLE:
        raise ToolExecutionError("PyAutoGUI is not installed or GUI is not accessible.")
    if pyautogui.size() == (0, 0):  # type: ignore
        raise ToolExecutionError(
            "Could not determine screen size. Ensure you are running in a graphical environment."
        )

    action = input_data.action
    logger.info(f"Performing GUI action: {action}")

    try:
        if action == "move":
            if not input_data.coordinates:
                raise ToolExecutionError(
                    "'coordinates' are required for 'move' action."
                )
            pyautogui.moveTo(  # type: ignore
                input_data.coordinates[0],
                input_data.coordinates[1],
                duration=input_data.duration_seconds,
            )
            return f"Mouse moved to {input_data.coordinates}."
        elif action == "click":
            pyautogui.click(input_data.coordinates)  # type: ignore
            coords = input_data.coordinates or pyautogui.position()  # type: ignore
            return f"Clicked at {coords}."
        elif action == "double_click":
            pyautogui.doubleClick(input_data.coordinates)  # type: ignore
            coords = input_data.coordinates or pyautogui.position()  # type: ignore
            return f"Double-clicked at {coords}."
        elif action == "type":
            if input_data.text_to_type is None:
                raise ToolExecutionError(
                    "'text_to_type' is required for 'type' action."
                )
            pyautogui.typewrite(input_data.text_to_type)  # type: ignore
            return f"Typed text: '{input_data.text_to_type[:50]}...'"
        elif action == "screenshot":
            if not input_data.screenshot_path:
                raise ToolExecutionError(
                    "'screenshot_path' is required for 'screenshot' action."
                )
            pyautogui.screenshot(input_data.screenshot_path)  # type: ignore
            return f"Screenshot saved to {input_data.screenshot_path}."
        else:
            # This should not be reached if Pydantic validation on 'action' is correct.
            raise ToolExecutionError(f"Unknown GUI action: {action}")
    except ToolExecutionError:  # Re-raise our own specific errors
        raise
    except Exception as e:  # Catch other pyautogui or unexpected errors
        logger.exception(f"An unexpected error occurred during GUI action '{action}'.")
        raise ToolExecutionError(
            f"An unexpected error occurred during GUI action '{action}': {e}"
        )


@register_tool(
    name="gui_find_and_click_image",
    input_model=GuiFindAndClickInput,
    description="Finds a provided image on the screen and moves to or clicks it. Requires a GUI environment.",
    tags=["gui", "pyautogui", "vision", "automation"],
    category="desktop",
    safe_mode=False,
    purpose="Visually locate and interact with a GUI element.",
)
def gui_find_and_click_image(input_data: GuiFindAndClickInput) -> str:
    """
    Locates an image on the screen and performs a mouse action on it.

    This is a powerful tool for interacting with GUI elements without relying on
    fixed coordinates. It repeatedly searches for the image until the timeout
    is reached. This requires the `opencv-python` library to be installed.

    :param input_data: An object specifying the template image and action.
    :type input_data: GuiFindAndClickInput
    :return: A string confirming the action or reporting failure.
    :rtype: str
    :raises ToolExecutionError: If pyautogui/opencv is unavailable, GUI cannot be accessed, or image is not found.
    """
    if not PYAUTOGUI_AVAILABLE:
        raise ToolExecutionError("PyAutoGUI is not installed or GUI is not accessible.")
    if pyautogui.size() == (0, 0):  # type: ignore
        raise ToolExecutionError(
            "Could not determine screen size. Ensure you are running in a graphical environment."
        )

    logger.info(
        f"Searching for image '{input_data.template_image_path}' on screen for {input_data.timeout_seconds}s."
    )

    location = None
    search_start_time = time.time()
    last_exception = None
    while time.time() - search_start_time < input_data.timeout_seconds:
        try:
            location = pyautogui.locateCenterOnScreen(  # type: ignore
                input_data.template_image_path, confidence=input_data.confidence
            )
            if location:
                logger.info(f"Image found at coordinates: {location}")
                break
            last_exception = (
                None  # Reset if search attempt was made without pyautogui error
            )
        except pyautogui.PyAutoGUIException as e:  # type: ignore
            # This can happen if the image file is not found or is invalid by pyautogui.
            logger.warning(
                f"PyAutoGUIException while searching for image '{input_data.template_image_path}': {e}"
            )
            last_exception = e  # type: ignore
            # Continue trying if within timeout
        except Exception as e:  # Catch other errors, e.g. if opencv-python is missing
            logger.error(
                f"Error during locateCenterOnScreen for '{input_data.template_image_path}'. "
                f"Is opencv-python installed? Error: {e}"
            )
            raise ToolExecutionError(
                f"Image searching failed for '{input_data.template_image_path}'. "
                f"Is 'opencv-python' installed? Error: {e}"
            )

        time.sleep(1)

    if not location:
        logger.warning(
            f"Image '{input_data.template_image_path}' not found on screen after timeout."
        )
        if last_exception:
            raise ToolExecutionError(
                f"Image '{input_data.template_image_path}' not found. Last search error: {last_exception}"
            )
        raise ToolExecutionError(
            f"Image '{input_data.template_image_path}' not found on screen after {input_data.timeout_seconds} seconds."
        )

    x, y = location
    action = input_data.action

    try:
        if action == "move_to":
            pyautogui.moveTo(x, y, duration=0.25)  # type: ignore
            return f"Mouse moved to image location ({x}, {y})."
        elif action == "click":
            pyautogui.click(x, y)  # type: ignore
            return f"Clicked on image at ({x}, {y})."
        elif action == "double_click":
            pyautogui.doubleClick(x, y)  # type: ignore
            return f"Double-clicked on image at ({x}, {y})."
        else:
            # This should not be reached if Pydantic validation is correct
            raise ToolExecutionError(
                f"Unknown action '{action}' specified for found image."
            )
    except Exception as e:  # Catch pyautogui action errors
        logger.exception(
            f"Error performing GUI action '{action}' on image at ({x},{y})."
        )
        raise ToolExecutionError(
            f"Error performing GUI action '{action}' on image: {e}"
        )
