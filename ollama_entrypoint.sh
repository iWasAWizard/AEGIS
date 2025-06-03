#!/bin/bash
set -euo pipefail

# Fail if OLLAMA_MODEL is not set
if [ -z "${OLLAMA_MODEL}" ]; then
  echo "❌ ERROR: OLLAMA_MODEL is not set. Please set it in your .env file or docker-compose.yml"
  exit 1
fi

echo "[OLLAMA] Starting Ollama server..."
ollama serve &

# Give the server a moment to come online
sleep 2

# Load the specified model
MODEL_NAME="${OLLAMA_MODEL:-hf.co/unsloth/granite-3.3-8b-instruct-GGUF:Q4_K_M}"
echo "[OLLAMA] Loading model: ${MODEL_NAME}"
ollama run "${MODEL_NAME}"

echo "[OLLAMA] Ollama is up!"
wait