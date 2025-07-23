# aegis/__main__.py
"""
Main entry point for running the AEGIS interactive shell.

This allows the shell to be started by running `python -m aegis`.
"""
import sys

from aegis.shell import AegisShell


def main():
    """Launches the AEGIS shell."""
    # Create an instance of the shell and run its command loop
    app = AegisShell()
    sys.exit(app.cmdloop())


if __name__ == "__main__":
    main()