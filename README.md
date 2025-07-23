# aegis/README.md
# 🛡️ AEGIS: Autonomous Agentic Framework

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/containerized-Docker-blue)](https://www.docker.com/)
[![Built with LangGraph](https://img.shields.io/badge/built%20with-LangGraph-orange)](https://github.com/langchain-ai/langgraph)

**AEGIS** is a framework for building autonomous AI agents that can plan and execute complex tasks. It's designed to be modular, easy to connect to different AI backends, and friendly for offline or "air-gapped" environments.

Instead of just responding to prompts, AEGIS agents can think step-by-step, use tools, and even ask for help to achieve a high-level goal.

---

## 🚀 Features

- **Complex Workflows:** Built on LangGraph, AEGIS lets you design agents that can loop, branch, and self-correct to solve multi-step problems.
- **Connect to Any Backend:** A flexible "Provider" system lets you easily switch between different AI backends (like the BEND stack, vLLM, OpenAI, or Ollama) just by changing a config file.
- **Reliable AI Responses:** Uses `Instructor` to force the AI's output into a clean, predictable format, which helps eliminate common errors and makes the agent more reliable.
- **See Every Thought:** With `LangFuse` integration, you get a detailed, visual trace of every thought and action the agent takes, making it much easier to debug and understand.
- **Long-Term Memory:** An agent can save and recall specific facts (like a user's name or a previous result) using a `Redis` backend, giving it a persistent "notebook."
- **Document Knowledge (RAG):** Connects to retrieval systems like BEND to let the agent pull information from your own documents, giving it a knowledge "library."
- **Hierarchical Agents:** Supports building a "manager" agent that can delegate tasks to a team of "specialist" agents, allowing you to solve more complex problems.
- **Human-in-the-Loop:** Includes a built-in way for agents to pause and ask for your input or approval before continuing with a task.
- **Automatic Testing:** Comes with a command-line tool to automatically test your agents against a set of examples, helping you make sure changes are making them better, not worse.
- **Extensible Toolset:** A clean and modular system makes it easy to add new tools and capabilities for your agent to use.

---

## 🏗️ Architecture

AEGIS is a standalone framework that acts as a client to a backend intelligence stack (like BEND).

```
+---------------------------------+      +--------------------------------+
|  Backend Intelligence Stack     |      |       AEGIS Docker Host        |
| (e.g., BEND: vLLM, Redis, etc.) |      |                                |
+---------------------------------+      | +----------------------------+ |
               ^                       | |      AEGIS Agent           | |
               | (API Calls)           | |                            | |
               v                       | | +--------------------------+ | |
+---------------------------------+      | | |   Agent Logic (LangGraph)| | |
|       AEGIS Providers           |      | | | (Plan->Execute->Verify)  | | |
|                                 |      | | +--------------------------+ | |
|  - VllmProvider                 |      | |             |              | |
|  - BendProvider                 |      | |             v              | |
|  - OpenAiProvider               |      | | +--------------------------+ | |
+---------------------------------+      | | | Tools & Executors        | | |
                                         | | +--------------------------+ | |
                                         +--------------------------------+
```

1.  **Backend Stack:** A service like [BEND](https://github.com/example/bend) provides the core AI models and services.
2.  **AEGIS Providers:** The `Provider` layer in AEGIS acts like a set of universal adapters, containing the logic to communicate with any specific backend.
3.  **AEGIS Agent:** The main AEGIS container runs the agent's "brain." It uses the configured `Provider` to think and make decisions.
4.  **Agent Logic:** The agent's workflow is defined as a graph, which allows it to plan a sequence of steps, execute them, and even verify the results.
5.  **Tools & Executors:** The agent's abilities are defined as `Tools` (e.g., `run_command`). These tools are built on top of `Executors`, which are the low-level clients that do the actual work (e.g., making an SSH connection).

---

## 🚀 Quick Start with Docker (Recommended)

### Prerequisites

1.  **Docker and Docker Compose installed.**
2.  **A running intelligence backend.** The companion [BEND](https://github.com/example/bend) project is the perfect match.
3.  An API key if you're using a commercial service like OpenAI.

### Steps

1.  **Configure Your Backend:**
    *   Open `backends.yaml` and make sure a profile points to your backend. If you're running BEND, the `vllm_local` profile should work automatically.
        ```yaml
        # backends.yaml
        backends:
          - profile_name: "vllm_local"
            type: "vllm"
            llm_url: "http://vllm:8000/v1/chat/completions"
        ```

2.  **Set Up Your Environment:**
    *   Copy `.env.example` to `.env`.
    *   Add any API keys (like `OPENAI_API_KEY`) or your LangFuse keys to this file.

3.  **Build and Run AEGIS:**
    From the project root, simply run:
    ```bash
    docker compose up --build -d
    ```

4.  **Open the UI:**
    Navigate to **`http://localhost:8000`** in your browser to access the AEGIS dashboard.

5.  **Run a Task:**
    *   Go to the "Launch" tab.
    *   Choose an "Agent Preset" (like `Verified Agent Flow`).
    *   Choose a "Backend Profile" (like `vllm_local`).
    *   Type in a prompt and click "Launch Task."
    *   You can watch the detailed trace of the agent's work in your LangFuse UI (running on port 12012 if you're using BEND).

---

## 🧠 Core Concepts

- **TaskState:** The "short-term memory" of a single task run, carrying all the information about the goal and its history.
- **Presets:** Reusable "recipes" in the `presets/` folder that define how an agent should behave for a certain type of task.
- **Providers:** The "plugs" that connect AEGIS to different AI backends. This is what makes the framework backend-agnostic.
- **Executors:** The low-level "drivers" that handle the raw work of talking to services like SSH, Redis, or a web browser.
- **Tools:** The specific abilities the agent can use, like `run_command` or `save_to_memory`. They are the building blocks of the agent's skills.
```