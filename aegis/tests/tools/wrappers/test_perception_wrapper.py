# aegis/tests/tools/wrappers/test_perception_wrapper.py
"""
Unit tests for the perception wrapper tools.
"""
from unittest.mock import MagicMock, patch
import uuid
from pathlib import Path

import pytest

from aegis.exceptions import ToolExecutionError
from aegis.tools.wrappers.perception import (
    capture_screenshot,
    CaptureScreenshotInput,
    ocr_read_screen_area,
    OcrReadScreenAreaInput,
    gui_find_and_read,
    GuiFindAndReadInput,
)
from aegis.tools.wrappers.gui import GuiActionInput

pytest.importorskip("pyautogui", reason="pyautogui not available for testing.")
pytest.importorskip("pytesseract", reason="pytesseract not available for testing.")


# --- Fixtures ---


@pytest.fixture
def mock_gui_action_for_local_screenshot(monkeypatch):
    """Mocks the underlying gui_action primitive for local screenshots."""
    mock = MagicMock(return_value="Local screenshot saved to /tmp/local.png")
    monkeypatch.setattr("aegis.tools.wrappers.perception.gui_action", mock)
    return mock


@pytest.fixture
def mock_ssh_executor_instance_for_remote_screenshot(monkeypatch):
    """Mocks SSHExecutor instance methods for remote screenshot tests."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = ""
    mock_instance.download.return_value = "Successfully downloaded remote file"

    mock_ssh_executor_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(
        "aegis.tools.wrappers.perception.SSHExecutor", mock_ssh_executor_class
    )

    mock_machine_obj = MagicMock()
    mock_machine_obj.platform = "linux"
    mock_get_machine = MagicMock(return_value=mock_machine_obj)
    monkeypatch.setattr("aegis.tools.wrappers.perception.get_machine", mock_get_machine)

    mock_uuid_gen = MagicMock()
    mock_uuid_gen.hex = "remoteABCDEF"
    monkeypatch.setattr(
        "aegis.tools.wrappers.perception.uuid.uuid4",
        MagicMock(return_value=mock_uuid_gen),
    )

    return mock_instance, mock_get_machine


@pytest.fixture
def mock_pyautogui_and_ocr_primitives(monkeypatch):
    """Mocks pyautogui and pytesseract for OCR tests (these don't use SSH)."""
    mock_pyautogui_lib = MagicMock()
    mock_pyautogui_lib.screenshot.return_value = "fake_image_data_for_ocr"
    mock_pyautogui_lib.locateOnScreen.return_value = (100, 100, 50, 50)
    mock_pyautogui_lib.size.return_value = (1920, 1080)
    monkeypatch.setattr("aegis.tools.wrappers.perception.pyautogui", mock_pyautogui_lib)

    mock_pytesseract_lib = MagicMock()
    mock_pytesseract_lib.image_to_string.return_value = "Extracted OCR Text from Mock"
    monkeypatch.setattr(
        "aegis.tools.wrappers.perception.pytesseract", mock_pytesseract_lib
    )

    # Patch time.time directly within aegis.tools.wrappers.perception if it's imported there
    # If time is imported as `import time` in perception.py, then this is correct:
    monkeypatch.setattr(
        "aegis.tools.wrappers.perception.time.time",
        MagicMock(side_effect=list(range(20))),
    )

    return mock_pyautogui_lib, mock_pytesseract_lib


# --- Tests ---


def test_capture_screenshot_local(mock_gui_action_for_local_screenshot):
    """Verify local screenshot delegates to gui_action."""
    input_data = CaptureScreenshotInput(
        machine_name="localhost", save_path="/tmp/local.png"
    )
    result = capture_screenshot(input_data)

    mock_gui_action_for_local_screenshot.assert_called_once()
    call_arg = mock_gui_action_for_local_screenshot.call_args[0][0]
    assert isinstance(call_arg, GuiActionInput)
    assert call_arg.action == "screenshot"
    assert call_arg.screenshot_path == "/tmp/local.png"

    assert result == "Local screenshot saved to /tmp/local.png"


def test_capture_screenshot_local_failure(mock_gui_action_for_local_screenshot):
    """Verify local screenshot propagates ToolExecutionError from gui_action."""
    mock_gui_action_for_local_screenshot.side_effect = ToolExecutionError(
        "pyautogui failed"
    )
    input_data = CaptureScreenshotInput(
        machine_name="localhost", save_path="/tmp/local.png"
    )
    with pytest.raises(ToolExecutionError, match="pyautogui failed"):
        capture_screenshot(input_data)


def test_capture_screenshot_remote_success(
    mock_ssh_executor_instance_for_remote_screenshot,
):
    """Verify remote screenshot uses SSH executor correctly."""
    executor_mock, _ = mock_ssh_executor_instance_for_remote_screenshot

    input_data = CaptureScreenshotInput(
        machine_name="remote-linux", save_path="/tmp/remote_save.png"
    )
    result = capture_screenshot(input_data)

    expected_remote_tmp_path = "/tmp/remoteABCDEF.png"

    # Check calls to executor's run method
    run_calls = executor_mock.run.call_args_list
    assert len(run_calls) == 2
    assert (
        run_calls[0][0][0] == f"DISPLAY=:0 scrot -d 1 '{expected_remote_tmp_path}'"
    )  # scrot command
    assert run_calls[1][0][0] == f"rm '{expected_remote_tmp_path}'"  # rm command

    executor_mock.download.assert_called_once_with(
        expected_remote_tmp_path, "/tmp/remote_save.png"
    )

    assert "Successfully captured screenshot from 'remote-linux'" in result
    assert "saved to '/tmp/remote_save.png'" in result


def test_capture_screenshot_remote_not_linux(
    mock_ssh_executor_instance_for_remote_screenshot,
):
    _, mock_get_machine = mock_ssh_executor_instance_for_remote_screenshot
    mock_machine_obj_windows = MagicMock()
    mock_machine_obj_windows.platform = "windows"
    mock_get_machine.return_value = mock_machine_obj_windows

    input_data = CaptureScreenshotInput(
        machine_name="remote-windows", save_path="s.png"
    )
    with pytest.raises(
        ToolExecutionError,
        match="Remote screenshot is currently only supported on Linux machines",
    ):
        capture_screenshot(input_data)


def test_capture_screenshot_remote_scrot_fails(
    mock_ssh_executor_instance_for_remote_screenshot,
):
    executor_mock, _ = mock_ssh_executor_instance_for_remote_screenshot
    # Simulate failure on the first run call (scrot)
    executor_mock.run.side_effect = [
        ToolExecutionError("scrot command failed via ssh"),
        "",
    ]

    input_data = CaptureScreenshotInput(machine_name="remote-linux", save_path="s.png")
    with pytest.raises(ToolExecutionError, match="scrot command failed via ssh"):
        capture_screenshot(input_data)
    executor_mock.download.assert_not_called()


def test_capture_screenshot_remote_download_fails(
    mock_ssh_executor_instance_for_remote_screenshot,
):
    executor_mock, _ = mock_ssh_executor_instance_for_remote_screenshot
    executor_mock.download.side_effect = ToolExecutionError(
        "SCP download error from executor"
    )

    input_data = CaptureScreenshotInput(machine_name="remote-linux", save_path="s.png")
    with pytest.raises(ToolExecutionError, match="SCP download error from executor"):
        capture_screenshot(input_data)
    # scrot might have been called
    assert executor_mock.run.call_count >= 1


def test_ocr_read_screen_area_success(mock_pyautogui_and_ocr_primitives):
    pyautogui_mock, pytesseract_mock = mock_pyautogui_and_ocr_primitives
    input_data = OcrReadScreenAreaInput(region=(0, 0, 100, 100))
    result = ocr_read_screen_area(input_data)

    pyautogui_mock.screenshot.assert_called_once_with(region=(0, 0, 100, 100))
    pytesseract_mock.image_to_string.assert_called_once_with("fake_image_data_for_ocr")
    assert result == "Extracted OCR Text from Mock"


def test_ocr_read_screen_area_no_text(mock_pyautogui_and_ocr_primitives):
    pyautogui_mock, pytesseract_mock = mock_pyautogui_and_ocr_primitives
    pytesseract_mock.image_to_string.return_value = "  \n  "
    input_data = OcrReadScreenAreaInput()
    result = ocr_read_screen_area(input_data)
    assert result == "[INFO] OCR found no text in the specified area."


def test_ocr_read_screen_area_pyautogui_fails(mock_pyautogui_and_ocr_primitives):
    pyautogui_mock, _ = mock_pyautogui_and_ocr_primitives
    pyautogui_mock.screenshot.side_effect = Exception("PyAutoGUI internal error")
    input_data = OcrReadScreenAreaInput()
    with pytest.raises(
        ToolExecutionError, match="OCR operation failed: PyAutoGUI internal error"
    ):
        ocr_read_screen_area(input_data)


def test_ocr_read_screen_area_pytesseract_fails(mock_pyautogui_and_ocr_primitives):
    _, pytesseract_mock = mock_pyautogui_and_ocr_primitives
    pytesseract_mock.image_to_string.side_effect = Exception(
        "Tesseract processing error"
    )
    input_data = OcrReadScreenAreaInput()
    with pytest.raises(
        ToolExecutionError, match="OCR operation failed: Tesseract processing error"
    ):
        ocr_read_screen_area(input_data)


def test_gui_find_and_read_success(mock_pyautogui_and_ocr_primitives):
    pyautogui_mock, pytesseract_mock = mock_pyautogui_and_ocr_primitives

    with patch(
        "aegis.tools.wrappers.perception.ocr_read_screen_area",
        return_value="Text near anchor",
    ) as mock_ocr_primitive_call:
        input_data = GuiFindAndReadInput(
            template_image_path="button.png",
            offset_box=(10, 10, 50, 20),
            timeout_seconds=3,
        )
        result = gui_find_and_read(input_data)

        pyautogui_mock.locateOnScreen.assert_called_with("button.png", confidence=0.9)
        expected_read_region = (100 + 10, 100 + 10, 50, 20)
        mock_ocr_primitive_call.assert_called_once()
        call_arg_input = mock_ocr_primitive_call.call_args[0][0]
        assert isinstance(call_arg_input, OcrReadScreenAreaInput)
        assert call_arg_input.region == expected_read_region
        assert result == "Text near anchor"


def test_gui_find_and_read_anchor_not_found(mock_pyautogui_and_ocr_primitives):
    pyautogui_mock, _ = mock_pyautogui_and_ocr_primitives
    pyautogui_mock.locateOnScreen.return_value = None

    input_data = GuiFindAndReadInput(
        template_image_path="missing.png", offset_box=(0, 0, 1, 1), timeout_seconds=1
    )
    with pytest.raises(
        ToolExecutionError,
        match="Anchor image 'missing.png' not found on screen after 1s.",
    ):
        gui_find_and_read(input_data)


def test_gui_find_and_read_opencv_error(mock_pyautogui_and_ocr_primitives):
    pyautogui_mock, _ = mock_pyautogui_and_ocr_primitives
    # Simulate the case where pyautogui.locateOnScreen itself raises, e.g. if opencv is missing
    # or image file is truly corrupt/unreadable by Pillow.
    pyautogui_mock.locateOnScreen.side_effect = Exception(
        "OpenCV error during image search"
    )

    input_data = GuiFindAndReadInput(
        template_image_path="template.png", offset_box=(0, 0, 1, 1), timeout_seconds=1
    )
    with pytest.raises(
        ToolExecutionError,
        match="Could not search for template image. Is 'opencv-python' installed? Error: OpenCV error during image search",
    ):
        gui_find_and_read(input_data)
