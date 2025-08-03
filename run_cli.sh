#!/bin/bash
# run_cli.sh
# A helper script to execute commands against the AEGIS CLI running inside
# the 'agent' container.
#
# Usage:
#   ./run_cli.sh                    - Drops you into the interactive (aegis) > shell.
#   ./run_cli.sh test list        - Runs a one-shot command and exits.
#   ./run_cli.sh task run "prompt"  - Runs a one-shot command with arguments.

# Check if any command-line arguments have been passed to the script.
if [ $# -gt 0 ]; then
  # If arguments are present, run in one-shot (non-interactive) mode.
  # We pass all arguments ("$@") to the shell inside the container.
  docker compose exec agent python -m aegis "$@"
else
  # If no arguments are present, run in interactive mode.
  # The '-it' flags are essential to allocate a pseudo-TTY and keep
  # stdin open, allowing for an interactive session.
  docker compose exec -it agent python -m aegis
fi