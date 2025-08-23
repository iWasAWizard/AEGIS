# aegis/__main__.py
"""
Main entry point for running the AEGIS interactive shell.

This allows the shell to be started by running `python -m aegis`.
It supports both interactive mode and one-shot command execution.
"""
import sys
import logging

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


def main():
    """Launches the AEGIS shell in interactive or one-shot mode."""

    # Filter out our custom flag so cmd2 doesn't see it
    cli_args = [arg for arg in sys.argv[1:] if arg != "--debug"]

    # Create an instance of the shell
    app = AegisShell()

    # Check if any arguments (other than our debug flag) were passed
    if cli_args:
        # One-shot mode: join arguments and execute as a single command
        command_to_run = " ".join(cli_args)
        # Use onecmd_plus_hooks to ensure startup() and other hooks run
        sys.exit(app.onecmd_plus_hooks(command_to_run))
    else:
        # Interactive mode: start the command loop
        sys.exit(app.cmdloop())


if __name__ == "__main__":
    main()
