# aegis/tests/tools/wrappers/test_gui_wrapper.py
"""
Unit tests for the pyautogui GUI wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.gui import (
    PYAUTOGUI_AVAILABLE,
    gui_action, GuiActionInput,
    gui_find_and_click_image, GuiFindAndClickInput
)

# Skip all tests in this file if pyautogui is not available (e.g., in a headless CI environment)
pytestmark = pytest.mark.skipif(not PYAUTOGUI_AVAILABLE, reason="pyautogui is not available or GUI is not accessible.")


# --- Fixtures ---

@pytest.fixture
def mock_pyautogui(monkeypatch):
    """Mocks all pyautogui functions used by the tools."""
    mock = MagicMock()
    mock.size.return_value = (1920, 1080)  # Simulate a screen
    mock.position.return_value = (100, 200)
    monkeypatch.setattr("aegis.tools.wrappers.gui.pyautogui", mock)
    return mock


# --- Tests for gui_action ---

@pytest.mark.parametrize(
    "action_name, action_input, expected_call, expected_args",
    [
        ("move", {"coordinates": (123, 456)}, "moveTo", (123, 456)),
        ("click", {"coordinates": (10, 20)}, "click", ()),
        ("double_click", {}, "doubleClick", ()),
        ("type", {"text_to_type": "hello world!"}, "typewrite", ("hello world!",)),
        ("screenshot", {"screenshot_path": "/tmp/test.png"}, "screenshot", ()),
    ]
)
def test_gui_action(mock_pyautogui, action_name, action_input, expected_call, expected_args):
    """Verify that each sub-action calls the correct pyautogui function."""
    base_input = {"action": action_name, "duration_seconds": 0}  # duration 0 for speed
    input_data = GuiActionInput(**(base_input | action_input))

    gui_action(input_data)

    # Assert that the correct function was called on the mock
    func_to_check = getattr(mock_pyautogui, expected_call)
    func_to_check.assert_called_once()

    # Optionally check arguments for some calls
    if expected_args:
        call_args = func_to_check.call_args[0]
        assert call_args == expected_args


def test_gui_action_requires_args():
    """Verify actions return an error if required arguments are missing."""
    # Move requires coordinates
    move_input = GuiActionInput(action="move")
    assert "[ERROR]" in gui_action(move_input)

    # Type requires text
    type_input = GuiActionInput(action="type")
    assert "[ERROR]" in gui_action(type_input)

    # Screenshot requires path
    ss_input = GuiActionInput(action="screenshot")
    assert "[ERROR]" in gui_action(ss_input)


# --- Tests for gui_find_and_click_image ---

def test_gui_find_and_click_image_success(mock_pyautogui, monkeypatch):
    """Verify the tool finds an image and correctly clicks it."""
    # Mock time.time to control the timeout loop
    monkeypatch.setattr("time.time", MagicMock(side_effect=[0, 1, 2]))

    # Mock locateCenterOnScreen to find the image on the first try
    mock_pyautogui.locateCenterOnScreen.return_value = (500, 600)

    input_data = GuiFindAndClickInput(
        template_image_path="/path/to/icon.png",
        action="click",
        timeout_seconds=5
    )
    result = gui_find_and_click_image(input_data)

    mock_pyautogui.locateCenterOnScreen.assert_called_once()
    # Check that click was called with the found coordinates
    mock_pyautogui.click.assert_called_once_with(x=500, y=600)
    assert "Clicked on image at (500, 600)" in result


def test_gui_find_and_click_image_not_found(mock_pyautogui, monkeypatch):
    """Verify the tool correctly times out and returns an error if the image is not found."""
    # Mock time.time to simulate the timeout
    # Will run for 0s, 1s, 2s, 3s, 4s, then the loop condition (5s) fails
    monkeypatch.setattr("time.time", MagicMock(side_effect=[0, 1, 2, 3, 4, 5]))

    # Mock locateCenterOnScreen to always return None
    mock_pyautogui.locateCenterOnScreen.return_value = None

    input_data = GuiFindAndClickInput(
        template_image_path="/path/to/missing.png",
        action="click",
        timeout_seconds=4
    )
    result = gui_find_and_click_image(input_data)

    assert mock_pyautogui.locateCenterOnScreen.call_count == 4
    assert "[ERROR] Image not found on screen" in result
