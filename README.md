# BEND
**Backend Enhanced Neural Dispatch**

[![Docker](https://img.shields.io/badge/containerized-Docker-blue)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

BEND is a locally-hosted, containerized backend stack designed to give your AI applications a solid foundation. It bundles together a suite of high-performance, open-source services for language models, document retrieval (RAG), voice, and more.

Think of it as a ready-to-run "AI power source" for your projects, letting you focus on building your application instead of managing complex infrastructure.

---

## What's in the Box? A Tour of the Services

BEND isn't a single application; it's a curated collection of services that work together seamlessly. Here’s a quick look at the key components and the role each one plays:

-   **vLLM (The Engine):** This is the high-performance server that runs your main language models. It's incredibly fast and efficient, especially on a GPU, and serves models through an OpenAI-compatible API.
-   **Ollama (The Specialist):** An easy-to-use and highly performant model server that excels at running GGUF-quantized models, especially on Apple Silicon. It's the new default for CPU-based and non-NVIDIA execution.
-   **Qdrant (The Library):** A professional-grade vector database. This is the heart of the RAG system, where the knowledge from your documents is stored, indexed, and made searchable.
-   **Redis (The Notebook):** A fast, in-memory database that provides a simple key-value store. This is used by agents to save and recall specific facts, giving them a persistent long-term memory.
-   **NeMo Guardrails (The Safety Inspector):** A security layer that can inspect an agent's proposed actions and block them if they violate pre-defined safety rules, preventing dangerous or unintended behavior.
-   **Whisper & Piper (The Ears & Voice):** These services handle speech-to-text and text-to-speech, allowing your applications to listen and speak through a simple, unified API.

## Architecture

All services run in their own Docker containers and communicate over a private network called `bend_bend-net`. This makes the entire stack self-contained and portable.

```
+-------------------------------------------------------------+
| BEND Docker Environment (Network: bend_bend-net)            |
|                                                             |
|  +-----------+   +----------+   +----------+   +----------+  |
|  |   vLLM    |   | Guardrails |   |  Qdrant  |   |  Redis   |  |
|  | (LLM API) |   | (Safety)   |   | (RAG DB) |   | (Memory) |  |
|  +-----------+   +----------+   +----------+   +----------+  |
|                                                             |
|  +-----------+   +----------+   +----------+                 |
|  |   Ollama  |   |  Whisper |   |   Piper  |                 |
|  | (LLM API) |   |  (STT)   |   |   (TTS)  |                 |
|  +-----------+   +----------+   +----------+                 |
|                                                             |
+-------------------------------------------------------------+
```

## 🚀 Quickstart

### 1. Prerequisites

-   Docker & Docker Compose
-   `git`
-   `yq` (e.g., `brew install yq` or `apt-get install yq`)
-   **(Optional) NVIDIA GPU** with the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

### 2. Setup

First, clone the repository and navigate into the directory.

```bash
git clone https://github.com/your-username/BEND.git
cd BEND
```

Next, you need to choose and configure a language model for vLLM.

```bash
# See a list of pre-configured models
./scripts/list-models.sh

# Download the full repository for a model (e.g., llama3)
./scripts/download-hf-model.sh "meta-llama/Meta-Llama-3-8B-Instruct"

# Configure the stack to use the chosen model
./scripts/switch-model.sh llama3
```

### 3. Start the Stack

You're now ready to launch all the BEND services.

-   **For CPU-only:**
    ```bash
    ./scripts/manage.sh up
    ```
-   **For NVIDIA GPU acceleration (recommended):**
    ```bash
    ./scripts/manage.sh up --gpu
    ```

### 4. Verify the Installation

Use the built-in healthcheck to make sure all services started correctly. It may take a minute for vLLM to download its model and become healthy.

```bash
./scripts/manage.sh healthcheck
```

Once all services show `[ OK ]`, you can explore the web interfaces for OpenWebUI (`http://localhost:12002`).

## ⚙️ Management

All stack management is handled by the `manage.sh` script:

-   `./scripts/manage.sh up`: Start all services.
-   `./scripts/manage.sh down`: Stop all services.
-   `./scripts/manage.sh restart [service_name]`: Restart all services or a specific one.
-   `./scripts/manage.sh logs [service_name]`: Tail the logs for all services or a specific one (e.g., `vllm`).
-   `./scripts/manage.sh status`: Show the status of all running containers.
-   `./scripts/manage.sh rebuild`: Force a rebuild of the Docker images without using the cache.

## 🎯 Ports Reference

| Port   | Service          |
|--------|------------------|
| 12002  | OpenWebUI        |
| 12003  | Whisper STT      |
| 12004  | Piper TTS        |
| 12005  | Glances          |
| 12006  | Qdrant (RAG)     |
| 12007  | Retriever API    |
| 12008  | Voice Proxy      |
| 12009  | Ollama           |
| 12010  | Redis            |
| 12011  | vLLM             |
| 12012  | NeMo Guardrails  |

## 🤝 Connecting with AEGIS

BEND is designed to be the perfect backend for the **AEGIS** agentic framework. Once BEND is up and running, you can follow the AEGIS quickstart guide to connect an autonomous agent to this stack.

## 💬 Philosophy

BEND is designed to be:

-   **Modular:** Swap pieces in and out as you need.
-   **Reproducible:** Builds reliably from a clean state, every time.
-   **Self-hosted:** Runs on your own hardware, with no cloud dependencies.
-   **Expandable:** Serves as a great foundation for building your own AI-powered applications.