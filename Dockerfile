# Stage 1: Build the React frontend
FROM node:23-alpine AS ui-builder

WORKDIR /app

COPY aegis/web/react_ui/package.json aegis/web/react_ui/package-lock.json* aegis/web/react_ui/vite.config.js ./aegis/web/react_ui/
RUN cd aegis/web/react_ui && npm install --legacy-peer-deps

COPY aegis/web/react_ui/ ./aegis/web/react_ui/

RUN cd aegis/web/react_ui && npm run build


# Stage 2: Build the Python backend
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt .
RUN apt-get update && apt-get install -y curl wget git firefox-esr nmap tcpdump jq python3-tk scrot libgl1-mesa-glx \
    libglib2.0-0 tesseract-ocr && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz && \
    tar -xzf geckodriver-v0.36.0-linux64.tar.gz -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver && \
    rm geckodriver-v0.36.0-linux64.tar.gz

COPY . .

COPY --from=ui-builder /app/aegis/web/react_ui/dist /app/aegis/web/react_ui/dist

CMD ["python", "-m", "aegis.serve_dashboard"]