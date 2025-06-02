"""Builds a sequential timeline of agent task execution, capturing the order and timestamps of actions."""

import matplotlib.pyplot as plt

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def save_timeline_plot(state, path):
    """
    save_timeline_plot.
    :param state: Description of state
    :param path: Description of path
    :type state: Any
    :type path: Any
    :return: Description of return value
    :rtype: Any
    """
    steps = state.get("result", [])
    labels = [f"Step {i + 1}" for i in range(len(steps))]
    durations = [s.get("duration", 1) for s in steps]
    plt.figure(figsize=(8, 4))
    plt.barh(labels, durations)
    plt.xlabel("Duration (s)")
    plt.title("Execution Timeline")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
