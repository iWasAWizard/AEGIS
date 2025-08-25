# aegis/registry.py
"""
Central tool registry and decorator for AEGIS.

- Idempotent registration (safe during module reloads).
- Clear, typed ToolEntry surface used by the agent & CLI.
- Back-compat shims: .callable alias, optional metadata fields used by the shell.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Type, Iterable, Tuple
import threading
import inspect

from pydantic import BaseModel

from aegis.exceptions import ToolNotFoundError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global registry (kept for backward-compat with existing imports)
TOOL_REGISTRY: Dict[str, "ToolEntry"] = {}

# Internal lock to synchronize concurrent registrations (e.g., parallel imports)
_REG_LOCK = threading.RLock()

# Discovery guard flag
_discovered = False


@dataclass(frozen=True)
class ToolEntry:
    """Shape consumed by the agent when executing tools.

    Required:
      - name: canonical tool name used by plans
      - input_model: Pydantic model for validation
      - func: callable implementing the tool
      - timeout: optional per-tool timeout in seconds

    Optional metadata (used by CLI / docs; safe defaults provided):
      - description: short human description
      - category: grouping label (e.g., "network", "filesystem")
      - tags: tuple of short tags
      - safe_mode: whether the tool is considered "safe" for default exposure
    """

    name: str
    input_model: Type[BaseModel]
    func: Callable[..., object]
    timeout: Optional[int] = None

    # --- metadata used by the shell/UI (optional) ---
    description: str = ""
    category: Optional[str] = None
    tags: Tuple[str, ...] = ()
    safe_mode: bool = True

    # Back-compat alias some older code expects
    @property
    def callable(self) -> Callable[..., object]:
        return self.func


def _same_signature(a: ToolEntry, b: ToolEntry) -> bool:
    # Consider the functional parts for idempotency;
    # metadata changes should not spam warnings during hot-reloads.
    return (
        a.name == b.name
        and a.input_model is b.input_model
        and a.func is b.func
        and a.timeout == b.timeout
    )


def register_tool(entry: ToolEntry) -> None:
    """Register a ToolEntry.

    Idempotent: re-registering the *same* tool is a no-op. If a different
    callable/model tries to claim the same name, we replace it but warn.
    """
    with _REG_LOCK:
        existing = TOOL_REGISTRY.get(entry.name)
        if existing is not None:
            if _same_signature(existing, entry):
                # Harmless re-import; refresh metadata quietly.
                # Keep the newer metadata but same func/model/timeout.
                TOOL_REGISTRY[entry.name] = ToolEntry(
                    name=existing.name,
                    input_model=existing.input_model,
                    func=existing.func,
                    timeout=existing.timeout,
                    description=entry.description or existing.description,
                    category=entry.category or existing.category,
                    tags=entry.tags or existing.tags,
                    safe_mode=(
                        entry.safe_mode
                        if entry.safe_mode is not None
                        else existing.safe_mode
                    ),
                )
                return
            logger.warning(
                "Re-registering tool '%s' with a different implementation.",
                entry.name,
            )
        TOOL_REGISTRY[entry.name] = entry
        logger.info("Registered tool: %s", entry.name)


def tool(
    name: str,
    input_model: Type[BaseModel],
    *,
    timeout: Optional[int] = None,
    description: str = "",
    category: Optional[str] = None,
    tags: Iterable[str] = (),
    safe_mode: bool = True,
):
    """Decorator to register a function as an AEGIS tool.

    Usage:
        @tool("ssh.exec", SSHExecInput, timeout=60, description="Run a remote command", category="network")
        async def run_ssh(...): ...
    """

    # freeze tags as a tuple for immutability inside dataclass
    tags_tuple: Tuple[str, ...] = tuple(tags or ())

    def _decorator(func: Callable[..., object]) -> Callable[..., object]:
        # Validate obvious misconfigurations early
        if not inspect.isfunction(func) and not inspect.iscoroutinefunction(func):
            raise TypeError("@tool can only decorate functions/coroutines")
        entry = ToolEntry(
            name=name,
            input_model=input_model,
            func=func,
            timeout=timeout,
            description=description or "",
            category=category,
            tags=tags_tuple,
            safe_mode=bool(safe_mode),
        )
        register_tool(entry)
        return func

    return _decorator


def get_tool(name: str) -> ToolEntry:
    try:
        return TOOL_REGISTRY[name]
    except KeyError:
        raise ToolNotFoundError(f"Tool not found: {name}")


def list_tools() -> Iterable[ToolEntry]:
    return list(TOOL_REGISTRY.values())


def ensure_discovered(importer: Optional[Callable[[], None]] = None) -> None:
    """Ensure tools are discovered exactly once in-process.

    - If `importer` is provided, it is called the first time to perform discovery.
    - Subsequent calls are no-ops.
    """
    global _discovered
    with _REG_LOCK:
        if _discovered:
            return
        if importer is not None:
            try:
                importer()
            except Exception as e:
                logger.error("Tool discovery failed: %s", e)
                # allow process to continue; registry may be partially filled
        _discovered = True


def reset_registry_for_tests() -> None:
    """Clear the registry and discovery guard (intended for tests only)."""
    global _discovered
    with _REG_LOCK:
        TOOL_REGISTRY.clear()
        _discovered = False
