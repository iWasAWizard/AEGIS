# aegis/utils/tooling.py
"""
Lightweight tool decorator & discovery helpers.

- @tool(name, input_model, timeout=None): attaches metadata to a callable so the registry
  can auto-register it. The callable MUST accept keyword-only `input_data: BaseModel`.

- discover_decorated(callables_from_module): retrieve all callables that were annotated.

This module is intentionally minimal and has no dependency on the executors.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel


_TOOL_ATTR = "__aegis_tool__"


def tool(name: str, input_model: type[BaseModel], timeout: Optional[int] = None):
    """
    Decorate a callable to mark it as a tool.

    The decorated function MUST have signature:
        def fn(*, input_data: BaseModel, **kwargs) -> Any
    """

    def _decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(
            fn,
            _TOOLS_ATTR_KEY,
            {
                "name": name,
                "input_model": input_model,
                "timeout": timeout,
            },
        )
        return fn

    return _decorate


# Backward compatible attribute name (constant kept private)
_TOOLS_ATTR_KEY = _TOOL_ATTR


def is_decorated_tool(obj: Any) -> bool:
    return hasattr(obj, _TOOLS_ATTR_KEY)


def get_tool_meta(obj: Any) -> Dict[str, Any]:
    return getattr(obj, _TOOLS_ATTR_KEY)


def discover_decorated(
    objs: Iterable[Any],
) -> List[Tuple[str, type[BaseModel], Optional[int], Callable[..., Any]]]:
    """
    Return list of (name, input_model, timeout, func) for decorated callables.
    """
    out: List[Tuple[str, type[BaseModel], Optional[int], Callable[..., Any]]] = []
    for o in objs:
        if is_decorated_tool(o):
            meta = get_tool_meta(o)
            out.append((meta["name"], meta["input_model"], meta.get("timeout"), o))
    return out
