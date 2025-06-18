# aegis/tests/tools/wrappers/test_perception_wrapper.py
"""
Unit tests for the perception wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.perception import (
    capture_screenshot,
    CaptureScreenshotInput,
    ocr_read_screen_area,
    OcrReadScreenAreaInput,
    gui_find_and_read,
    GuiFindAndReadInput,
)

# Mark this entire module to be skipped if pyautogui is not available
pytest.importorskip("pyautogui", reason="pyautogui not available for testing.")
pytest.importorskip("pytesseract", reason="pytesseract not available for testing.")


# --- Fixtures ---


@pytest.fixture
def mock_gui_action(monkeypatch):
    """Mocks the underlying gui_action primitive."""
    mock = MagicMock(return_value="Local screenshot saved to /tmp/local.png")
    monkeypatch.setattr("aegis.tools.wrappers.perception.gui_action", mock)
    return mock


@pytest.fixture
def mock_ssh_executor(monkeypatch):
    """Mocks the SSHExecutor for remote screenshot tests."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = "scrot success"
    mock_instance.download.return_value = "download success"
    monkeypatch.setattr(
        "aegis.tools.wrappers.perception.SSHExecutor",
        MagicMock(return_value=mock_instance),
    )
    monkeypatch.setattr("aegis.tools.wrappers.perception.get_machine", MagicMock())
    return mock_instance


@pytest.fixture
def mock_pyautogui_and_ocr(monkeypatch):
    """Mocks pyautogui and pytesseract for OCR tests."""
    mock_pyautogui = MagicMock()
    mock_pyautogui.screenshot.return_value = "fake_image_data"
    mock_pyautogui.locateOnScreen.return_value = (100, 100, 50, 50)  # Box object
    monkeypatch.setattr("aegis.tools.wrappers.perception.pyautogui", mock_pyautogui)

    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = "Extracted OCR Text"
    monkeypatch.setattr("aegis.tools.wrappers.perception.pytesseract", mock_pytesseract)

    # Also need to mock time for loops
    monkeypatch.setattr("time.time", MagicMock(side_effect=[0, 1, 2, 3]))


# --- Tests ---


def test_capture_screenshot_local(mock_gui_action):
    """Verify local screenshot delegates to gui_action."""
    input_data = CaptureScreenshotInput(
        machine_name="localhost", save_path="/tmp/local.png"
    )
    result = capture_screenshot(input_data)
    mock_gui_action.assert_called_once()
    assert "Local screenshot saved" in result


def test_capture_screenshot_remote(mock_ssh_executor):
    """Verify remote screenshot uses the SSH executor."""
    input_data = CaptureScreenshotInput(
        machine_name="remote-linux", save_path="/tmp/remote.png"
    )
    # Mock the machine platform to be linux
    mock_ssh_executor.machine.platform = "linux"
    result = capture_screenshot(input_data)

    assert mock_ssh_executor.run.call_count == 2  # one for scrot, one for rm
    assert mock_ssh_executor.download.call_count == 1
    assert "Successfully captured screenshot" in result


def test_ocr_read_screen_area(mock_pyautogui_and_ocr):
    """Verify OCR tool calls pyautogui and pytesseract."""
    input_data = OcrReadScreenAreaInput(region=(0, 0, 100, 100))
    result = ocr_read_screen_area(input_data)

    assert result == "Extracted OCR Text"


def test_gui_find_and_read(mock_pyautogui_and_ocr):
    """Verify the find_and_read tool locates an image and then calls OCR."""
    input_data = GuiFindAndReadInput(
        template_image_path="button.png", offset_box=(10, 10, 50, 20)
    )
    result = gui_find_and_read(input_data)

    # Check that it tried to find the image
    pyautogui_mock = MagicMock()
    pyautogui_mock.locateOnScreen.assert_called_once_with("button.png", confidence=0.9)

    # Check that it then called OCR
    pytesseract_mock = MagicMock()
    pytesseract_mock.image_to_string.assert_called_once()
    assert result == "Extracted OCR Text"
