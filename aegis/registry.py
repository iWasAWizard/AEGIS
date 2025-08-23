# aegis/registry.py
"""
Auto-registering tool registry.

- ToolEntry: metadata + callable
- register_tool() / get_tool()
- ensure_discovered(): import aegis.tools.builtins and register all @tool adapters
- audit_executors(): scan aegis.executors for *_result methods that are not registered; log WARNINGs

This design minimizes fragility:
- You add a new executor method (e.g., `FooExecutor.bar_result`) → audit will warn if it's not registered.
- You add a new adapter in aegis.tools.builtins with @tool → it auto-registers on first use.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type

from pydantic import BaseModel

from aegis.exceptions import ToolNotFoundError
from aegis.utils.logger import setup_logger
from aegis.utils.tooling import discover_decorated

logger = setup_logger(__name__)


@dataclass
class ToolEntry:
    name: str
    input_model: Type[BaseModel]
    func: Callable[..., Any]
    timeout: Optional[int] = None


_REGISTRY: Dict[str, ToolEntry] = {}
_DISCOVERED = False
_AUDITED = False


def register_tool(
    name: str,
    input_model: Type[BaseModel],
    func: Callable[..., Any],
    timeout: Optional[int] = None,
) -> None:
    _REGISTRY[name] = ToolEntry(
        name=name, input_model=input_model, func=func, timeout=timeout
    )


def _iter_module_callables(mod) -> list:
    return [getattr(mod, k) for k in dir(mod)]


def _discover_builtin_tools() -> None:
    """
    Import aegis.tools.builtins (and any submodules) and register all decorated adapters.
    """
    try:
        pkg = importlib.import_module("aegis.tools")
    except ModuleNotFoundError:
        return

    # Import builtins.py explicitly
    try:
        builtins_mod = importlib.import_module("aegis.tools.builtins")
        for name, input_model, timeout, func in discover_decorated(
            _iter_module_callables(builtins_mod)
        ):
            register_tool(name, input_model, func, timeout)
    except ModuleNotFoundError:
        pass

    # Import any submodules under aegis.tools.* and collect decorated callables too
    try:
        pkg_path = pkg.__path__  # type: ignore[attr-defined]
        for finder, modname, ispkg in pkgutil.walk_packages(
            pkg_path, prefix=pkg.__name__ + "."
        ):
            try:
                m = importlib.import_module(modname)
                for name, input_model, timeout, func in discover_decorated(
                    _iter_module_callables(m)
                ):
                    register_tool(name, input_model, func, timeout)
            except Exception as e:
                logger.error(f"Tool discovery error in module {modname}: {e}")
    except Exception:
        pass


def _audit_missing_tools() -> None:
    """
    Scan aegis.executors.* for public methods ending with '_result'.
    If any are not present in the registry, log a WARNING so nothing is silently forgotten.
    """
    try:
        exe_pkg = importlib.import_module("aegis.executors")
    except ModuleNotFoundError:
        return

    missing = []
    try:
        pkg_path = exe_pkg.__path__  # type: ignore[attr-defined]
        for finder, modname, ispkg in pkgutil.walk_packages(
            pkg_path, prefix=exe_pkg.__name__ + "."
        ):
            try:
                m = importlib.import_module(modname)
            except Exception:
                continue
            for _, obj in inspect.getmembers(m, inspect.isclass):
                if obj.__module__ != m.__name__:
                    continue
                # look for methods ending in _result
                for meth_name, meth in inspect.getmembers(obj, inspect.isfunction):
                    if not meth_name.endswith("_result"):
                        continue
                    # Heuristic tool key suggestion: <module-base>.<method-base>
                    module_base = modname.split(".")[-1].replace("_exec", "")
                    method_base = meth_name.removesuffix("_result")
                    suggested = f"{module_base}.{method_base}"
                    if suggested not in _REGISTRY:
                        missing.append(suggested)
        if missing:
            uniq = sorted(set(missing))
            logger.warning(
                "Tool registry audit: found executor methods with no adapters registered. "
                "Consider adding @tool adapters in aegis.tools.builtins for: %s",
                ", ".join(uniq),
            )
    except Exception as e:
        logger.error(f"Tool audit failed: {e}")


def ensure_discovered() -> None:
    global _DISCOVERED, _AUDITED
    if not _DISCOVERED:
        _discover_builtin_tools()
        _DISCOVERED = True
    if not _AUDITED:
        _audit_missing_tools()
        _AUDITED = True


def get_tool(name: str) -> ToolEntry:
    ensure_discovered()
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ToolNotFoundError(f"Tool '{name}' is not registered.")
