# aegis/__main__.py
"""
Main entry point for running the AEGIS interactive shell.

This allows the shell to be started by running `python -m aegis`.
It supports both interactive mode and one-shot command execution.
"""
from __future__ import annotations

import sys
import logging
import argparse

# --- CLI Log Level Configuration ---
# This logic MUST run before any other aegis modules are imported.
# It ensures that the root logger is configured with the correct level
# before any module-level loggers are instantiated.

# Check if --debug flag is present in the arguments
is_debug_mode = "--debug" in sys.argv
log_level = logging.DEBUG if is_debug_mode else logging.INFO

# Set the root logger's level.
logging.getLogger().setLevel(log_level)

# Now that the log level is set, import and log the env knobs.
from aegis.utils.env_report import log_env_knobs

log_env_knobs()  # uses its own logger if none is provided

# Now that the log level is set, we can import the rest of the application.
from aegis.shell import AegisShell


def main(argv: list[str] | None = None) -> int:
    """
    Launches the AEGIS shell in interactive or one-shot mode.
    - Supports your original passthrough mode: `python -m aegis docker pull alpine`
    - Supports explicit `-c/--command "..."` one-shot execution
    - Supports `--no-intro` to suppress the banner
    - Keeps `--debug` handling exactly as before
    """
    # Use provided argv or sys.argv[1:]
    argv = list(sys.argv[1:] if argv is None else argv)

    # Strip our debug flag so it doesn't confuse argparse or cmd2
    argv_wo_debug = [arg for arg in argv if arg != "--debug"]

    # Top-level flags that affect launcher behavior only
    parser = argparse.ArgumentParser(prog="python -m aegis", add_help=True)
    parser.add_argument(
        "-c",
        "--command",
        dest="command",
        help='Run a single AEGIS CLI command and exit (e.g., -c "docker pull alpine")',
    )
    parser.add_argument(
        "--no-intro",
        action="store_true",
        help="Suppress the intro banner in interactive mode",
    )
    # Parse only known flags; anything left is treated as a passthrough command
    args, remainder = parser.parse_known_args(argv_wo_debug)

    # Create an instance of the shell
    app = AegisShell()
    if args.no_intro:
        app.intro = None

    try:
        # Explicit one-shot via -c/--command
        if args.command:
            app.onecmd_plus_hooks(args.command)
            return 0

        # Back-compat passthrough: any remaining tokens become a command
        if remainder:
            command_to_run = " ".join(remainder)
            app.onecmd_plus_hooks(command_to_run)
            return 0

        # Interactive mode
        app.cmdloop()
        return 0
    except (KeyboardInterrupt, EOFError):
        # Graceful exit on Ctrl+C / Ctrl+D
        return 0
    finally:
        # Ensure cmd2 cleanup if available
        try:
            app.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
