# aegis/utils/timeout.py
"""
Simple watchdog for synchronous tool adapters.

- run_with_watchdog(func, timeout_s, *args, **kwargs) -> (ok, value_or_exc)
  Executes func in a thread; if it fails to finish within timeout_s, returns (False, TimeoutError()).
  The underlying work may still be running; use per-executor timeouts to prevent zombies.

Notes:
- This is a soft guard to guarantee the orchestrator gets control back.
- Executors SHOULD still enforce their own subprocess/network timeouts.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Tuple


def run_with_watchdog(
    fn: Callable[..., Any], timeout_s: int | float, *args, **kwargs
) -> Tuple[bool, Any]:
    result_box = {"done": False, "value": None}

    def _runner():
        try:
            result_box["value"] = fn(*args, **kwargs)
        except Exception as e:  # bubble actual exception to caller path
            result_box["value"] = e
        finally:
            result_box["done"] = True

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout=timeout_s)

    if not result_box["done"]:
        return False, TimeoutError(
            f"Tool execution exceeded watchdog timeout ({timeout_s}s)"
        )
    return True, result_box["value"]
