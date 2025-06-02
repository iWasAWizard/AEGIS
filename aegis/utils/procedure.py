"""Loads multi-step procedures from file and presents them as a callable list of instructions."""

import csv

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def save_procedure_csv(state, path):
    """
    save_procedure_csv.
    :param state: Description of state
    :param path: Description of path
    :type state: Any
    :type path: Any
    :return: Description of return value
    :rtype: Any
    """
    steps = state.get("result", [])
    with open(path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Step", "Action Taken", "Expected Result", "Notes"])
        for i, step in enumerate(steps):
            writer.writerow(
                [
                    i + 1,
                    step.get("command", "N/A"),
                    step.get("expected", "N/A"),
                    step.get("notes", ""),
                ]
            )
