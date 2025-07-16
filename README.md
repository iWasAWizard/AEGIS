# 🛡️ AEGIS: Autonomous Agentic Framework

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/containerized-Docker-blue)](https://www.docker.com/)
[![Built with LangGraph](https://img.shields.io/badge/built%20with-LangGraph-orange)](https://github.com/langchain-ai/langgraph)

**AEGIS** is a modular, backend-agnostic, and "air-gapped friendly" autonomous agent framework built on Python and LangGraph. It is designed to act as an intelligent "Cerebral Cortex," capable of planning and executing complex tasks by connecting to any number of external intelligence backends (like local LLMs, commercial APIs, or other services).

The core philosophy is to provide a **powerful, configurable engine** for experts to build and deploy autonomous systems, while remaining flexible enough to integrate with any tool or service.

---

## 🏗️ Architecture

AEGIS is a fully standalone framework. It operates as a client that connects to backend services defined in `backends.yaml`.

```
+---------------------------------+      +--------------------------------+
|      External Backend(s)        |      |       AEGIS Docker Host        |
| (e.g., Local KoboldCPP, OpenAI) |      |                                |
+---------------------------------+      | +----------------------------+ |
               ^                       | |      AEGIS Agent           | |
               | (API Calls via        | |                            | |
               |  Backend Provider)   | | +--------------------------+ | |
               v                       | | |   Agent Execution Graph  | | |
+---------------------------------+      | | | (Plan -> Execute ->)     | | |
|       AEGIS Core Engine         |      | | +--------------------------+ | |
|                                 |      | |             |              | |
|  - Backend Loader & Providers   |      | |             v              | |
|  - Tool Registry & Execution    |      | | +--------------------------+ | |
|  - State Management (TaskState) |      | | |    Tool Executor       | | |
|                                 |      | | +--------------------------+ | |
+---------------------------------+      | +----------------------------+ |
                                         +--------------------------------+
```

1.  **Backend Services:** Run anywhere—on your local machine, on another server, or in the cloud. AEGIS connects to them via URLs defined in `backends.yaml`.
2.  **AEGIS Core Engine:** The AEGIS Docker container runs the agent. It uses a "Backend Provider" to abstract away the details of communicating with the configured backend.
3.  **Agent Execution Graph:** The agent's control loop, powered by LangGraph, uses the configured backend to create plans and executes them using its internal toolset.

---

## 🚀 Quick Start with Docker (Recommended)

### Prerequisites

1.  **Docker and Docker Compose installed.**
2.  **An accessible LLM backend.** For local testing, you can run a service like [KoboldCPP](https://github.com/LostRuins/koboldcpp) on your host machine.
3.  An API key if you plan to use a commercial service like OpenAI.

### Steps

1.  **Configure Your Backend:**
    *   Open the `backends.yaml` file in the project root.
    *   Edit a profile to point to your backend. For a local KoboldCPP instance, the default `bend_local` profile should work if it is running on your host.
        ```yaml
        # backends.yaml
        backends:
          - profile_name: "bend_local"
            type: "bend"
            llm_url: "http://host.docker.internal:12009/api/v1/generate"
        ```

2.  **Configure Environment Secrets:**
    *   Copy the `.env.example` file to `.env`.
    *   If you are using a backend that requires an API key (like OpenAI), add it to the `.env` file:
        ```
        OPENAI_API_KEY=sk-...
        ```

3.  **Build and Run AEGIS:**
    From the project root, use the standard `docker compose` command.
    ```bash
    docker compose up --build -d
    ```

4.  **Access the UI:**
    Open your web browser and navigate to **`http://localhost:8000`**. You should see the AEGIS web dashboard.

5.  **Run a Task:**
    *   Go to the "Launch" tab.
    *   In the "Execution Overrides" section, ensure the `backend_profile` matches the one you configured in `backends.yaml` (e.g., `bend_local` or `openai_gpt4`).
    *   Enter a prompt and launch the task.