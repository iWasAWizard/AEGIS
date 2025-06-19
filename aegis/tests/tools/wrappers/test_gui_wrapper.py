# aegis/tests/tools/wrappers/test_gui_wrapper.py
"""
Unit tests for the pyautogui GUI wrapper tools.
"""
from unittest.mock import MagicMock

import pytest

from aegis.tools.wrappers.gui import (
    gui_action,
    GuiActionInput,
    gui_find_and_click_image,
    GuiFindAndClickInput,
)

# Skip all tests in this file if pyautogui is not available
pytest.importorskip(
    "pyautogui", reason="pyautogui is not available or GUI is not accessible."
)


# --- Fixtures ---


@pytest.fixture
def mock_pyautogui(monkeypatch):
    """Mocks all pyautogui functions used by the tools."""
    mock = MagicMock()
    mock.size.return_value = (1920, 1080)  # Simulate a screen
    mock.position.return_value = (100, 200)
    # Mock locateCenterOnScreen to "find" an image
    mock.locateCenterOnScreen.return_value = (500, 600)
    monkeypatch.setattr("aegis.tools.wrappers.gui.pyautogui", mock)
    return mock


# --- Tests for gui_action ---


@pytest.mark.parametrize(
    "action_name, action_input, expected_call_name, expected_args",
    [
        ("move", {"coordinates": (123, 456)}, "moveTo", (123, 456)),
        ("click", {"coordinates": (10, 20)}, "click", ()),
        ("double_click", {}, "doubleClick", ()),
        ("type", {"text_to_type": "hello world!"}, "typewrite", ("hello world!",)),
        (
            "screenshot",
            {"screenshot_path": "/tmp/test.png"},
            "screenshot",
            ("/tmp/test.png",),
        ),
    ],
)
def test_gui_action(
    mock_pyautogui, action_name, action_input, expected_call_name, expected_args
):
    """Verify that each sub-action calls the correct pyautogui function."""
    base_input = {"action": action_name, "duration_seconds": 0.5}
    full_input_dict = {**base_input, **action_input}

    # Handle the special case for moveTo where duration is a keyword argument
    if action_name == "move":
        full_input_dict["duration_seconds"] = 0.5
        input_data = GuiActionInput(**full_input_dict)
        gui_action(input_data)
        func_to_check = getattr(mock_pyautogui, expected_call_name)
        func_to_check.assert_called_once_with(
            expected_args[0], expected_args[1], duration=0.5
        )
        return

    input_data = GuiActionInput(**full_input_dict)
    gui_action(input_data)

    func_to_check = getattr(mock_pyautogui, expected_call_name)

    if expected_args:
        func_to_check.assert_called_once_with(*expected_args)
    else:
        func_to_check.assert_called_once()


def test_gui_action_requires_args(mock_pyautogui):
    """Verify actions return an error if required arguments are missing."""
    move_input = GuiActionInput(action="move")
    assert "[ERROR]" in gui_action(move_input)

    type_input = GuiActionInput(action="type")
    assert "[ERROR]" in gui_action(type_input)

    ss_input = GuiActionInput(action="screenshot")
    assert "[ERROR]" in gui_action(ss_input)


# --- Tests for gui_find_and_click_image ---


def test_gui_find_and_click_image_success(mock_pyautogui, monkeypatch):
    """Verify the tool finds an image and correctly clicks it."""
    monkeypatch.setattr("time.time", MagicMock(side_effect=[0, 1, 2]))

    input_data = GuiFindAndClickInput(
        template_image_path="/path/to/icon.png", action="click", timeout_seconds=5
    )
    result = gui_find_and_click_image(input_data)

    mock_pyautogui.locateCenterOnScreen.assert_called_once()
    mock_pyautogui.click.assert_called_once_with(x=500, y=600)
    assert "Clicked on image at (500, 600)" in result


def test_gui_find_and_click_image_not_found(mock_pyautogui, monkeypatch):
    """Verify the tool correctly times out and returns an error if the image is not found."""
    monkeypatch.setattr("time.time", MagicMock(side_effect=[0, 1, 2, 3, 4, 5]))
    mock_pyautogui.locateCenterOnScreen.return_value = None

    input_data = GuiFindAndClickInput(
        template_image_path="/path/to/missing.png", action="click", timeout_seconds=4
    )
    result = gui_find_and_click_image(input_data)

    assert mock_pyautogui.locateCenterOnScreen.call_count >= 1
    assert "[ERROR] Image not found on screen" in result
