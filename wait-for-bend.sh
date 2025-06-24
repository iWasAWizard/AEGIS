#!/bin/sh
# wait-for-koboldcpp.sh

set -e

# The host and port should match the service name and port in the BEND docker-compose.yml
host="koboldcpp"
port="12009"
cmd="$@"

# Use KOBOLDCPP_API_URL if it's set, otherwise construct from host/port
api_url="${KOBOLDCPP_API_URL:-http://$host:$port/api/v1/model}"

echo "Waiting for KoboldCPP at $api_url..."

# Use curl to check if the API is responsive. The /api/v1/model endpoint is a good health check.
# We loop until curl returns a 0 exit code (success).
# We use a simple counter to avoid an infinite loop and provide feedback.
counter=0
while ! curl -s -f "$api_url" > /dev/null; do
  counter=$((counter+1))
  if [ $counter -gt 60 ]; then
    echo "KoboldCPP did not become available after 5 minutes. Exiting."
    exit 1
  fi
  >&2 echo "KoboldCPP is unavailable - sleeping for 5 seconds (attempt $counter)..."
  sleep 5
done

>&2 echo "KoboldCPP is up - executing command"
exec $cmd