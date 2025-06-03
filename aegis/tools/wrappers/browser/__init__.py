"""
Browser wrapper tools initializer.

Exposes all browser-based agent tools for centralized discovery and import.
"""

from . import capture_web_state, web_interact, web_snapshot_compare

__all__ = [
    "capture_web_state",
    "web_interact",
    "web_snapshot_compare",
]
