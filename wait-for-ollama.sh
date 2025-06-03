#!/bin/sh
set -e

RETRIES=60
DELAY=1

echo "[AGENT] Waiting for Ollama to be available at ${OLLAMA_HOST}..."

for i in $(seq 1 $RETRIES); do
  if curl -s "${OLLAMA_HOST}/api/tags" > /dev/null; then
    echo "[AGENT] Ollama is responding."
    break
  fi
  echo "[AGENT] Attempt ${i}/${RETRIES}: Ollama not ready yet..."
  sleep $DELAY
done

if ! curl -s "${OLLAMA_HOST}/api/tags" > /dev/null; then
  echo >&2 "[FATAL] Ollama did not become ready after ${RETRIES} attempts. Exiting."
  exit 1
fi

MODELS=$(curl -s "${OLLAMA_HOST}/api/tags" | jq '.models | length')

if [ "$MODELS" -eq 0 ]; then
  echo >&2 "[FATAL] Ollama is running but has no models available."
  echo >&2 "[FATAL] Use 'ollama pull <model>' to add one before starting the system."
  exit 1
fi

echo "[AGENT] Ollama is up!"

exec uvicorn aegis.serve_dashboard:app --reload --reload-dir /app --host 0.0.0.0 --port 8000
