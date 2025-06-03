# Stage 1: Build the React frontend
FROM node:23-alpine AS ui-builder

WORKDIR /app
COPY . /app

WORKDIR /app/aegis/web/react_ui
RUN npm install && npm run build

# Stage 2: Build the Python backend
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt /app

# Install OS dependencies + Python packages
RUN apt-get update && apt-get install -y curl wget git firefox-esr nmap tcpdump jq && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || (echo '❌ pip install failed!' && exit 1)

# Install GeckoDriver for Selenium tooling
RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz && \
    tar -xzf geckodriver-v0.36.0-linux64.tar.gz -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver && \
    rm geckodriver-v0.36.0-linux64.tar.gz

# Copy over everything else
#COPY . /app

WORKDIR /app

COPY wait-for-ollama.sh /app

RUN chmod -x ./wait-for-ollama.sh

# COPY THE FRONTEND LAST to avoid being overwritten or missing
COPY --from=ui-builder /app/aegis/web/react_ui/dist /app/aegis/web/react_ui/dist

# Launch script waits for Ollama, then runs uvicorn
CMD ["./wait-for-ollama.sh"]
