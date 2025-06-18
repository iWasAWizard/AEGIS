#!/bin/bash
set -euo pipefail # -e: exit on error, -u: unbound variables are errors, -o pipefail: pipeline fails if any command fails

# OLLAMA_MODEL should be passed from docker-compose.yml via .env file
if [ -z "${OLLAMA_MODEL}" ]; then
  echo "❌ ERROR: OLLAMA_MODEL environment variable is not set."
  echo "Please ensure it's defined in your .env file and passed to the ollama service."
  exit 1
fi

echo "[OLLAMA ENTRYPOINT] Starting Ollama server in background..."
ollama serve &
PID=$! # Get PID of ollama serve

# Give the server a brief moment to initialize.
# `ollama pull` will also wait or retry to some extent if the server isn't immediately available.
echo "[OLLAMA ENTRYPOINT] Allowing a few seconds for Ollama server to initialize..."
sleep 5 # Increased to 5 seconds for a bit more buffer

echo "[OLLAMA ENTRYPOINT] Pulling model: ${OLLAMA_MODEL} (this may take a while if not present)..."
# The `ollama pull` command will interact with the `ollama serve` process.
# If `ollama serve` isn't ready, `ollama pull` might fail or retry.
if ollama pull "${OLLAMA_MODEL}"; then
  echo "[OLLAMA ENTRYPOINT] Model ${OLLAMA_MODEL} pulled successfully or already present."
else
  echo "❌ ERROR: Failed to pull model ${OLLAMA_MODEL}. Please check model name and network."
  echo "Ensure the Ollama server (ollama serve) started correctly."
  # Attempt to kill the background server if pull fails, then exit
  if kill $PID 2>/dev/null; then
    echo "[OLLAMA ENTRYPOINT] Ollama server (PID: $PID) stopped due to pull failure."
  fi
  exit 1
fi

echo "[OLLAMA ENTRYPOINT] Ollama setup complete. Server running in background (PID: $PID)."
echo "[OLLAMA ENTRYPOINT] Container will remain active while Ollama server is running."

# Wait for the ollama serve process to exit.
# If ollama serve exits for any reason, this script will exit, and the container will stop.
wait $PID

echo "[OLLAMA ENTRYPOINT] Ollama server (PID: $PID) has exited."