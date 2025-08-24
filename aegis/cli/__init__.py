# aegis/cli/__init__.py
"""
CLI command-set bootstrap for AEGIS.

Call `register_all_cli_commands(app)` during cmd2 shell init to register all
executors' commands. Each import is guarded so partial environments
(e.g., missing docker/k8s libs) won't crash the shell.
"""
from __future__ import annotations

import cmd2


def register_all_cli_commands(app: cmd2.Cmd) -> None:
    """
    Register all available command sets.

    Parameters
    ----------
    app : cmd2.Cmd
        The running cmd2 application instance (e.g., your AegisShell).
    """

    def safe_register(modpath: str, func: str = "register") -> None:
        try:
            mod = __import__(modpath, fromlist=[func])
            getattr(mod, func)(app)
        except Exception as e:
            # Non-fatal: optional stacks may be unavailable at runtime.
            app.perror(f"[warn] Skipping CLI module {modpath}: {e}")

    # Order is not semantically important; keep stable for predictable help output.
    safe_register("aegis.cli.compose")
    safe_register("aegis.cli.docker")
    safe_register("aegis.cli.kubernetes")
    safe_register("aegis.cli.ssh")
    safe_register("aegis.cli.redis")
    safe_register("aegis.cli.http")
    safe_register("aegis.cli.gitlab")
    safe_register("aegis.cli.local")
