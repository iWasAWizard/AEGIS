# aegis/tools/wrappers/perception.py
"""
High-level tools that give the agent "perception" or "vision" capabilities,
such as capturing screenshots and performing Optical Character Recognition (OCR).
"""
import shlex
import time
import uuid
from typing import Optional, Tuple

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.ssh_exec import SSHExecutor
from aegis.registry import register_tool
from aegis.tools.wrappers.gui import gui_action, GuiActionInput
from aegis.utils.logger import setup_logger
from aegis.utils.machine_loader import get_machine

try:
    import pyautogui
    from PIL import Image

    PYAUTOGUI_AVAILABLE = True
except (ImportError, Exception):
    PYAUTOGUI_AVAILABLE = False

try:
    import pytesseract

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

logger = setup_logger(__name__)


# --- Input Models ---


class CaptureScreenshotInput(BaseModel):
    """Input model for capturing a screenshot.

    :ivar save_path: The local file path to save the screenshot to.
    :vartype save_path: str
    :ivar machine_name: The machine to capture from. Defaults to 'localhost'.
    :vartype machine_name: str
    """

    save_path: str = Field(
        ...,
        description="The local file path to save the screenshot to (e.g., 'reports/screenshot.png').",
    )
    machine_name: str = Field(
        "localhost",
        description="The machine to capture the screenshot from. Defaults to 'localhost'.",
    )


class OcrReadScreenAreaInput(BaseModel):
    """Input model for performing OCR on a screen area.

    :ivar region: Optional bounding box (left, top, width, height) to capture.
                  If None, captures the whole screen.
    :vartype region: Optional[Tuple[int, int, int, int]]
    """

    region: Optional[Tuple[int, int, int, int]] = Field(
        None,
        description="Optional bounding box (left, top, width, height) to capture. If None, captures the whole screen.",
    )


class GuiFindAndReadInput(BaseModel):
    """Input for finding an image and reading text in an area relative to it.

    :ivar template_image_path: The file path to the image to find on screen (the anchor).
    :vartype template_image_path: str
    :ivar offset_box: The bounding box (left, top, width, height) relative to the
                      anchor image's top-left corner where text should be read.
    :vartype offset_box: Tuple[int, int, int, int]
    :ivar timeout_seconds: How long to search for the anchor image.
    :vartype timeout_seconds: int
    """

    template_image_path: str = Field(
        ..., description="The file path to the image to find on screen (the anchor)."
    )
    offset_box: Tuple[int, int, int, int] = Field(
        ...,
        description="The bounding box (left, top, width, height) relative to the anchor image's "
        "top-left corner where text should be read.",
    )
    timeout_seconds: int = Field(
        10, description="How long to search for the anchor image."
    )


# --- Tools ---


@register_tool(
    name="capture_screenshot",
    input_model=CaptureScreenshotInput,
    description="Captures a screenshot of the entire screen of a target machine and saves it locally.",
    tags=["perception", "screenshot", "gui", "remote"],
    category="desktop",
    safe_mode=False,
)
def capture_screenshot(input_data: CaptureScreenshotInput) -> str:
    """
    Captures a screenshot from either the local machine or a remote machine.

    If `machine_name` is 'localhost', it uses `pyautogui` locally.
    If `machine_name` is a remote host, it uses SSH to run the `scrot` command,
    downloads the resulting image, and cleans up the remote file. This requires
    the remote machine to be a Linux host with a running X server and `scrot` installed.

    :param input_data: An object specifying the target machine and local save path.
    :type input_data: CaptureScreenshotInput
    :return: A confirmation message with the path to the saved screenshot.
    :rtype: str
    """
    logger.info(
        f"Request to capture screenshot from '{input_data.machine_name}' and save to '{input_data.save_path}'."
    )

    # --- Case 1: Local Screenshot ---
    if input_data.machine_name.lower() == "localhost":
        logger.info("Performing local screenshot.")
        gui_input = GuiActionInput(
            action="screenshot",
            screenshot_path=input_data.save_path,
            coordinates=None,
            text_to_type=None,
            duration_seconds=0.1,
        )
        # Assuming gui_action will raise ToolExecutionError on failure.
        return gui_action(gui_input)

    # --- Case 2: Remote Screenshot ---
    logger.info("Performing remote screenshot via SSH.")
    try:
        machine = get_machine(input_data.machine_name)
        if machine.platform != "linux":
            raise ToolExecutionError(
                "Remote screenshot is currently only supported on Linux machines (requires 'scrot')."
            )

        executor = SSHExecutor(machine)

        remote_tmp_path = f"/tmp/{uuid.uuid4().hex}.png"

        # The `DISPLAY=:0` part is crucial for capturing the screen in a standard desktop session.
        # The `-d 1` adds a 1-second delay to allow for UI transitions.
        capture_command = f"DISPLAY=:0 scrot -d 1 {shlex.quote(remote_tmp_path)}"
        logger.info(f"Executing remote capture command: {capture_command}")

        # executor.run() will raise ToolExecutionError if scrot fails or DISPLAY is not found.
        # scrot is usually silent on success.
        executor.run(capture_command)
        logger.info(
            f"Remote screenshot captured to {remote_tmp_path} on {input_data.machine_name}."
        )

        logger.info(
            f"Downloading remote file '{remote_tmp_path}' to '{input_data.save_path}'"
        )
        # executor.download() will raise ToolExecutionError if download fails.
        download_message = executor.download(remote_tmp_path, input_data.save_path)
        logger.info(download_message)

        # Clean up the temporary file on the remote host
        cleanup_command = f"rm {shlex.quote(remote_tmp_path)}"
        logger.info(f"Cleaning up remote file: {cleanup_command}")
        executor.run(
            cleanup_command
        )  # Will raise if rm fails, but we might not care as much.

        return (
            f"Successfully captured screenshot from '{input_data.machine_name}' "
            f"and saved to '{input_data.save_path}'."
        )

    except ToolExecutionError:  # Catch errors from executor calls
        raise  # Re-raise to be handled by execute_tool
    except Exception as e:  # Catch other unexpected errors
        logger.exception(
            f"An unexpected error occurred during remote screenshot capture."
        )
        raise ToolExecutionError(
            f"An unexpected error occurred during remote screenshot: {e}"
        )


@register_tool(
    name="ocr_read_screen_area",
    input_model=OcrReadScreenAreaInput,
    description="Captures either a specified area of the screen, or the full screen,"
    " and returns any text found within it using OCR.",
    tags=["ocr", "perception", "gui", "vision"],
    category="desktop",
    safe_mode=True,
)
def ocr_read_screen_area(input_data: OcrReadScreenAreaInput) -> str:
    """
    Performs Optical Character Recognition (OCR) on a specified region of the screen.

    This tool takes a screenshot of the given screen area (or the full screen if no
    region is specified) and uses the Tesseract OCR engine to extract any visible
    text. It requires `pyautogui`, `Pillow`, and `pytesseract` to be installed.

    :param input_data: An object specifying the screen region to read.
    :type input_data: OcrReadScreenAreaInput
    :return: The extracted text as a single string.
    :rtype: str
    :raises ToolExecutionError: If dependencies are missing or GUI is inaccessible.
    """
    if not PYAUTOGUI_AVAILABLE or not PYTESSERACT_AVAILABLE:
        raise ToolExecutionError(
            "OCR functionality requires pyautogui, Pillow, and pytesseract."
        )
    if pyautogui.size() == (0, 0):  # type: ignore
        raise ToolExecutionError(
            "Could not determine screen size. Ensure you are in a graphical environment."
        )

    logger.info(
        f"Performing OCR on screen region: {input_data.region or 'Full Screen'}"
    )
    try:
        screenshot_image = pyautogui.screenshot(region=input_data.region)  # type: ignore
        extracted_text = pytesseract.image_to_string(screenshot_image).strip()  # type: ignore

        logger.info(f"OCR extracted {len(extracted_text)} characters.")
        return (
            extracted_text
            if extracted_text
            else "[INFO] OCR found no text in the specified area."
        )
    except Exception as e:  # Includes pytesseract.TesseractNotFoundError etc.
        logger.exception(f"An error occurred during OCR operation.")
        raise ToolExecutionError(f"OCR operation failed: {e}")


@register_tool(
    name="gui_find_and_read",
    input_model=GuiFindAndReadInput,
    description="Finds a template image (anchor) on screen, then reads text from a specified area next to it.",
    tags=["ocr", "perception", "gui", "vision", "automation"],
    category="desktop",
    safe_mode=False,
)
def gui_find_and_read(input_data: GuiFindAndReadInput) -> str:
    """
    A high-level tool to visually find an anchor and read text from a relative position.

    This tool is powerful for automating GUIs where element IDs are not available.
    It first locates a given `template_image_path` on the screen. Once found, it
    uses the image's location as an anchor point and then performs OCR on a new
    region defined by the `offset_box` relative to that anchor.

    :param input_data: Specifies the anchor image and the relative box to read from.
    :type input_data: GuiFindAndReadInput
    :return: The text extracted from the target area, or an error.
    :rtype: str
    :raises ToolExecutionError: If dependencies are missing or GUI is inaccessible.
    """
    if not PYAUTOGUI_AVAILABLE:
        raise ToolExecutionError("This tool requires pyautogui and opencv-python.")
    if pyautogui.size() == (0, 0):  # type: ignore
        raise ToolExecutionError(
            "Could not determine screen size. Ensure GUI is available."
        )

    logger.info(
        f"Attempting to find anchor image '{input_data.template_image_path}' to read text."
    )

    anchor_location = None
    search_start_time = time.time()
    while time.time() - search_start_time < input_data.timeout_seconds:
        try:
            # pyautogui.locateOnScreen returns a Box(left, top, width, height) object
            anchor_location = pyautogui.locateOnScreen(  # type: ignore
                input_data.template_image_path, confidence=0.9
            )
            if anchor_location:
                logger.info(f"Found anchor image at: {anchor_location}")
                break
        except (
            Exception
        ) as e:  # This can be pyautogui.ImageNotFoundException if opencv-python is missing
            raise ToolExecutionError(
                f"Could not search for template image. Is 'opencv-python' installed? Error: {e}"
            )
        time.sleep(1)

    if not anchor_location:
        raise ToolExecutionError(
            f"Anchor image '{input_data.template_image_path}' not found on screen after {input_data.timeout_seconds}s."
        )

    anchor_left, anchor_top, _, _ = anchor_location
    offset_left, offset_top, read_width, read_height = input_data.offset_box

    # Calculate the absolute screen coordinates of the region to read from
    read_region = (
        anchor_left + offset_left,
        anchor_top + offset_top,
        read_width,
        read_height,
    )

    return ocr_read_screen_area(OcrReadScreenAreaInput(region=read_region))
