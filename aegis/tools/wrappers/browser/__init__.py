"""Initialization for browser wrapper tools.

Ensures all browser-based agent tools are discoverable and imported."""

# tools/wrappers/browser/__init__.py

# Expose all primitive tools for easy import/registration
from .capture_web_state import *
from .web_interact import *
from .web_snapshot_compare import *
