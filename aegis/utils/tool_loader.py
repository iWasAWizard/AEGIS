# aegis/utils/tool_loader.py
"""
Utilities for discovering and importing tool modules.

Goals:
- Import built-in tools under `aegis.tools` (all submodules).
- Import user plugins from a `plugins/` directory (optional).
- Be idempotent: safe to call multiple times without duplicate registrations.
- Never crash the process if a single plugin is broken; log and continue.
"""
from __future__ import annotations

from importlib import import_module
from pkgutil import walk_packages
from pathlib import Path
import sys
import runpy
import traceback
from typing import Set

from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# Track what we've imported so we do not reload plugins repeatedly.
_IMPORTED_MODULES: Set[str] = set()
_EXECUTED_FILES: Set[Path] = set()


def _import_pkg_recursive(pkg_name: str) -> None:
    """Import a package and all its submodules."""
    try:
        pkg = import_module(pkg_name)
        # Mark the root so we don't spam logs on subsequent calls.
        _IMPORTED_MODULES.add(pkg_name)
    except Exception as e:
        logger.error("Failed to import package '%s': %s", pkg_name, e)
        return
    try:
        for m in walk_packages(getattr(pkg, "__path__", []), prefix=pkg.__name__ + "."):
            name = m.name
            if name in _IMPORTED_MODULES:
                continue
            try:
                import_module(name)
                _IMPORTED_MODULES.add(name)
                logger.debug("Imported tool module: %s", name)
            except Exception:
                logger.error(
                    "Error importing module %s\n%s", name, traceback.format_exc()
                )
    except Exception as e:
        logger.error("Error walking package '%s': %s", pkg_name, e)


def _execute_python_file(path: Path) -> None:
    """Execute a standalone Python file (plugin) once per process.

    Using runpy ensures file-local relative imports work when written as scripts.
    """
    try:
        rpath = path.resolve()
    except Exception:
        rpath = path

    try:
        if rpath in _EXECUTED_FILES:
            return
        runpy.run_path(str(rpath), run_name=f"plugin:{rpath}")
        _EXECUTED_FILES.add(rpath)
        logger.debug("Executed plugin file: %s", rpath)
    except Exception:
        logger.error(
            "Error executing plugin file %s\n%s", rpath, traceback.format_exc()
        )


def import_plugins_from_dir(plugins_dir: Path) -> None:
    """Import all .py files and packages under a directory as plugins."""
    try:
        plugins_dir = plugins_dir.resolve()
    except Exception:
        # Fall back to raw path if resolve() fails (e.g., broken symlink).
        pass

    if not plugins_dir.exists():
        return
    if not plugins_dir.is_dir():
        logger.warning("plugins path %s is not a directory; skipping", plugins_dir)
        return

    # Add to sys.path once so packages within can be imported by name
    try:
        sys_path_entry = str(plugins_dir)
        if sys_path_entry not in sys.path:
            sys.path.append(sys_path_entry)
    except Exception:
        # Non-fatal; we can still execute files directly below.
        logger.warning("Could not add %s to sys.path; continuing", plugins_dir)

    # Import packages and modules
    for p in plugins_dir.rglob("*.py"):
        # Skip dunder & cache paths
        if any(part.startswith("__") or part == "__pycache__" for part in p.parts):
            continue

        # If this file lives inside a Python package (has __init__.py up its tree
        # within plugins_dir), prefer importing by module name; otherwise execute file.
        pkg_root = None
        for parent in reversed(p.parents):
            try:
                if (parent / "__init__.py").exists():
                    # Ensure parent is within plugins_dir using path semantics
                    try:
                        parent.relative_to(plugins_dir)
                        pkg_root = parent
                        break
                    except Exception:
                        # Parent is not within plugins_dir; keep searching upward
                        continue
            except Exception:
                break

        if pkg_root:
            try:
                rel = p.relative_to(plugins_dir).with_suffix("")
                mod_name = ".".join(rel.parts)
            except Exception:
                # Fallback: execute directly if we cannot compute a safe module name
                _execute_python_file(p)
                continue

            if mod_name in _IMPORTED_MODULES:
                continue
            try:
                import_module(mod_name)
                _IMPORTED_MODULES.add(mod_name)
                logger.debug("Imported plugin module: %s", mod_name)
            except Exception:
                logger.error(
                    "Error importing plugin module %s\n%s",
                    mod_name,
                    traceback.format_exc(),
                )
        else:
            _execute_python_file(p)


def import_all_tools(
    *, include_plugins: bool = True, plugins_dir: Path | None = None
) -> None:
    """Discover and import tools from built-ins and optional plugins."""
    # Built-ins
    _import_pkg_recursive("aegis.tools")

    # User plugins
    if include_plugins:
        if plugins_dir is None:
            plugins_dir = Path.cwd() / "plugins"
        import_plugins_from_dir(plugins_dir)


__all__ = ["import_all_tools", "import_plugins_from_dir"]
