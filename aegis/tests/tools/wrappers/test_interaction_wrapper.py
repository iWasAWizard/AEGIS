# aegis/tests/tools/wrappers/test_interaction_wrapper.py
"""
Unit tests for the human interaction wrapper tools.
"""
from aegis.tools.wrappers.interaction import (
    ask_human_for_input,
    AskHumanForInputInput,
)


def test_ask_human_for_input():
    """Verify the tool returns the correct confirmation string."""
    input_data = AskHumanForInputInput(question="Do you want to proceed?")
    result = ask_human_for_input(input_data)

    assert "The agent has paused" in result
    assert "Do you want to proceed?" in result
