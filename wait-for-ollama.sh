#!/bin/sh
set -e # Exit immediately if a command exits with a non-zero status.

# OLLAMA_API_URL will be like "http://ollama:11434/api/generate"
# We need the base part for a health check, e.g., "http://ollama:11434"
if [ -z "${OLLAMA_API_URL}" ]; then
  echo "❌ ERROR: OLLAMA_API_URL is not set. Cannot check Ollama status."
  exit 1
fi

# Derive base URL (e.g., http://ollama:11434)
# This assumes OLLAMA_API_URL ends with /api/generate
OLLAMA_BASE_URL=$(echo "$OLLAMA_API_URL" | sed 's|/api/generate$||')
HEALTH_CHECK_ENDPOINT="${OLLAMA_BASE_URL}/api/tags" # /api/tags is a good simple check

RETRIES=${WAIT_RETRIES:-60} # Number of retries (default 60)
DELAY=${WAIT_DELAY:-2}    # Delay between retries in seconds (default 2)

echo "[AEGIS AGENT] Waiting for Ollama to be available at ${HEALTH_CHECK_ENDPOINT}..."

# Loop until Ollama is ready or retries are exhausted
count=0
until curl -s -f "${HEALTH_CHECK_ENDPOINT}" > /dev/null 2>&1; do
  count=$((count + 1))
  if [ "${count}" -gt "${RETRIES}" ]; then
    echo "❌ ERROR: Ollama did not become ready at ${HEALTH_CHECK_ENDPOINT} after ${RETRIES} attempts."
    exit 1
  fi
  echo "[AEGIS AGENT] Attempt ${count}/${RETRIES}: Ollama not ready yet. Retrying in ${DELAY}s..."
  sleep "${DELAY}"
done

echo "[AEGIS AGENT] Ollama is up and responding at ${HEALTH_CHECK_ENDPOINT}!"

# Execute the main application command passed as arguments to this script
# (e.g., from Dockerfile CMD: ["./wait-for-ollama.sh", "python", "-m", "aegis.serve_dashboard"])
exec "$@"