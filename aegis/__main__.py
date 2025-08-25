# aegis/__main__.py
"""
Main entry point for running the AEGIS interactive shell.

This allows the shell to be started by running `python -m aegis`.
It supports both interactive mode and one-shot command execution.
"""
from __future__ import annotations

import sys
import logging

# --- CLI Log Level & Intercepted Flags ---
# This logic MUST run before any other aegis modules are imported.
# It ensures the root logger is configured before module-level loggers exist.

# Flags intercepted here (removed before passing to command processing):
#   --debug      : sets root logger to DEBUG
#   --dry-run    : enables global dry-run mode (no side-effectful executor calls)
_INTERCEPT_FLAGS = {"--debug", "--dry-run"}

is_debug_mode = "--debug" in sys.argv
log_level = logging.DEBUG if is_debug_mode else logging.INFO

# Set the root logger's level.
logging.getLogger().setLevel(log_level)

# Now that the log level is set, import and log the env knobs.
from aegis.utils.env_report import log_env_knobs  # noqa: E402

log_env_knobs()  # uses its own logger if none is provided

# Import remaining pieces after logging has been configured.
from aegis.shell import AegisShell  # noqa: E402

try:
    # Optional: only needed if --dry-run is used
    from aegis.utils.dryrun import dry_run  # noqa: E402
except Exception:  # pragma: no cover
    dry_run = None  # type: ignore


def _extract_flags(argv: list[str]) -> tuple[list[str], set[str]]:
    """
    Split out our process-level flags from the user command tokens.

    Returns:
        (cli_args_without_intercepted_flags, seen_flags)
    """
    seen = {flag for flag in argv if flag in _INTERCEPT_FLAGS}
    filtered = [a for a in argv if a not in _INTERCEPT_FLAGS]
    return filtered, seen


def main(argv: list[str] | None = None) -> int:
    """Launches the AEGIS shell in interactive or one-shot mode.

    Returns an integer exit code suitable for sys.exit().
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    # Strip intercept flags and record which were present
    cli_args, seen = _extract_flags(argv)

    # Apply global dry-run if requested (before shell construction)
    if "--dry-run" in seen and dry_run is not None:
        try:
            dry_run.enabled = True
        except Exception:
            # Non-fatal; continue without toggling
            pass

    # Create an instance of the shell
    app = AegisShell()

    # One-shot mode when arguments (other than our intercept flags) are present
    if cli_args:
        command_to_run = " ".join(cli_args)
        # Use onecmd_plus_hooks to ensure startup() and other hooks run
        app.onecmd_plus_hooks(command_to_run)
        # Propagate status determined by CLI handlers via print_result()
        return int(getattr(app, "_last_exit_code", 0))

    # Interactive mode: start the command loop
    try:
        app.cmdloop()
        return int(getattr(app, "_last_exit_code", 0))
    except SystemExit as e:
        # If cmd loop raised SystemExit, honor its code
        try:
            return int(e.code)  # type: ignore[arg-type]
        except Exception:
            return 0


if __name__ == "__main__":
    sys.exit(main())
