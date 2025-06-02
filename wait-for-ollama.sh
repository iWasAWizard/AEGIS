#!/bin/sh
set -e

echo "[*] Waiting for Ollama to initialize..."
until curl -s http://ollama:11434/api/tags > /dev/null; do
  sleep 1
done

echo "[*] Ollama is up!"
exec uvicorn aegis.serve_dashboard:app --reload --reload-dir /app --host 0.0.0.0 --port 8000
