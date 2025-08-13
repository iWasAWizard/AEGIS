# aegis/plugins/vision_tools.py
"""
A tool for multimodal perception using a Vision Language Model (VLM).
"""
import io
from typing import Optional, Tuple

from pydantic import BaseModel, Field

from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

try:
    import pyautogui
    from PIL import Image

    PYAUTOGUI_AVAILABLE = True
except (ImportError, Exception):
    PYAUTOGUI_AVAILABLE = False


logger = setup_logger(__name__)


class DescribeScreenAreaInput(BaseModel):
    """Input for describing an area of the screen using a VLM.

    :ivar question: The question to ask the VLM about the captured image.
    :vartype question: str
    :ivar region: Optional bounding box (left, top, width, height) to capture.
                  If None, captures the whole screen.
    :vartype region: Optional[Tuple[int, int, int, int]]
    """

    question: str = Field(
        ..., description="The question to ask the VLM about the captured image."
    )
    region: Optional[Tuple[int, int, int, int]] = Field(
        None,
        description="Optional bounding box (left, top, width, height) to capture. If None, captures the whole screen.",
    )


@register_tool(
    name="describe_screen_area",
    input_model=DescribeScreenAreaInput,
    description="Captures a screenshot of a specified screen area (or the full screen) and asks a vision model to describe it based on a question. Returns a textual description of the visual elements.",
    tags=["vision", "vlm", "perception", "gui", "provider-aware"],
    category="desktop",
    safe_mode=False,
)
async def describe_screen_area(
    input_data: DescribeScreenAreaInput, state: TaskState, provider: BackendProvider
) -> str:
    """
    Captures a screen area and uses a VLM to get a textual description.

    :param input_data: An object specifying the screen region and question.
    :type input_data: DescribeScreenAreaInput
    :param state: The current agent task state.
    :type state: TaskState
    :param provider: The active backend provider instance.
    :type provider: BackendProvider
    :return: The textual description from the VLM.
    :rtype: str
    """
    if not PYAUTOGUI_AVAILABLE:
        raise ToolExecutionError(
            "Visual perception tools require pyautogui and Pillow to be installed."
        )
    if pyautogui.size() == (0, 0):  # type: ignore
        raise ToolExecutionError(
            "Could not determine screen size. Ensure you are in a graphical environment."
        )

    logger.info(
        f"Capturing screen area '{input_data.region or 'full screen'}' for VLM description."
    )

    try:
        # 1. Capture the image using pyautogui
        screenshot_image: Image.Image = pyautogui.screenshot(region=input_data.region)  # type: ignore

        # 2. Convert the PIL Image to bytes in memory
        image_bytes_io = io.BytesIO()
        screenshot_image.save(image_bytes_io, format="PNG")
        image_bytes = image_bytes_io.getvalue()

        # 3. Call the provider's vision method
        description = await provider.get_visual_description(
            prompt=input_data.question, image_bytes=image_bytes
        )
        logger.info(f"VLM returned description: '{description[:100]}...'")
        return description

    except NotImplementedError:
        raise ToolExecutionError(
            f"The current backend '{state.runtime.backend_profile}' does not support vision."
        )
    except Exception as e:
        logger.exception("An unexpected error occurred during screen description.")
        raise ToolExecutionError(f"Failed to describe screen area: {e}")
