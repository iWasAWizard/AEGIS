# 🛡️ AEGIS: Autonomous Agentic Framework

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/containerized-Docker-blue)](https://www.docker.com/)
[![Built with LangGraph](https://img.shields.io/badge/built%20with-LangGraph-orange)](https://github.com/langchain-ai/langgraph)

**AEGIS** is a framework for building, running, and observing autonomous AI agents. It's designed to be a modular and backend-agnostic "brain" that can plan and execute complex tasks by connecting to any number of AI backends.

Instead of just responding to prompts, AEGIS agents can think step-by-step, use a wide variety of tools, recover from errors, and even ask for human help to achieve a high-level goal.

---

## ✨ Key Features

-   **Complex Workflows:** Built on LangGraph, AEGIS lets you design agents that can loop, branch, and self-correct to solve multi-step problems.
-   **Connect to Any Backend:** A flexible "Provider" system lets you easily switch between different AI backends (like the **BEND** stack, a local vLLM server, or commercial APIs like OpenAI) just by changing a config file.
-   **Reliable AI Responses:** Uses **Instructor** to force the AI's output into a clean, predictable format. This guarantees the agent's plans are always valid, eliminating a major source of errors.
-   **Persistent Memory:** An agent can save and recall specific facts (like a user's name or a previous result) using a **Redis** backend, giving it a persistent "notebook."
-   **Hierarchical Agents (MoE):** Supports building a "manager" agent that can delegate tasks to a team of "specialist" agents, allowing you to solve more complex problems.
-   **Human-in-the-Loop:** Includes a built-in way for agents to pause and ask for your input or approval before continuing with a task.
-   **Automated Testing:** Comes with a command-line tool to automatically test your agents against a set of examples, helping you ensure that changes are making them better, not worse.
-   **Extensible Toolset:** A clean and modular system makes it easy to add new tools and capabilities—from shell commands to browser automation—for your agent to use.

---

## 🏗️ Architecture

AEGIS is a standalone framework that acts as a client to an intelligence backend. Its architecture is designed in layers to keep it modular and easy to understand.

```
+---------------------------------+      +--------------------------------+
|  Backend Intelligence Stack     |      |       AEGIS Docker Host        |
| (e.g., BEND or OpenAI API)      |      |                                |
+---------------------------------+      | +----------------------------+ |
               ^                       | |      AEGIS Agent           | |
               | (API Calls)           | |                            | |
               v                       | | +--------------------------+ | |
+---------------------------------+      | | |   Agent Logic (LangGraph)| | |
|       AEGIS Providers           |      | | | (Plan->Execute->Verify)  | | |
|                                 |      | | +--------------------------+ | |
|  - VllmProvider                 |      | |             |              | |
|  - KoboldcppProvider            |      | |             v              | |
|  - OpenAiProvider               |      | | +--------------------------+ | |
+---------------------------------+      | | | Tools & Executors        | | |
                                         | | +--------------------------+ | |
                                         +--------------------------------+
```

1.  **Backend Stack:** A service like the companion [BEND](https://github.com/your-username/BEND) project provides the core AI models and services.
2.  **AEGIS Providers:** The `Provider` layer in AEGIS acts like a set of universal adapters, containing the logic to communicate with any specific backend.
3.  **AEGIS Agent:** The main AEGIS container runs the agent's "brain." It uses the configured `Provider` to think and make decisions.
4.  **Agent Logic (The Graph):** The agent's workflow is defined as a graph. This allows it to plan a sequence of steps, execute them, and even verify the results in a loop.
5.  **Tools & Executors:** The agent's abilities are defined as `Tools` (e.g., `run_command`). These tools are built on top of `Executors`, which are the low-level clients that do the actual work (e.g., making an SSH connection).

---

## 🚀 Quickstart

The best way to run AEGIS is by connecting it to the **BEND** backend stack. For a complete walkthrough, please see the **[Combined BEND + AEGIS Quickstart Guide](./docs/Combined_Quickstart.md)**.

If you want to run AEGIS standalone against a commercial API like OpenAI, please see the **[AEGIS Standalone Quickstart Guide](./docs/Quickstart_Guide.md)**.

The basic steps are:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/AEGIS.git
    cd AEGIS
    ```

2.  **Configure Your Environment:**
    Copy the example environment file and fill in your details.
    ```bash
    cp .env.example .env
    # Now, edit the .env file
    ```

3.  **Build and Run AEGIS:**
    ```bash
    docker compose up --build -d
    ```

4.  **Open the UI:**
    Navigate to **`http://localhost:8000`** in your browser to access the AEGIS dashboard.

---

## 🧠 Core Concepts

-   **TaskState:** The "short-term memory" of a single task run. It's a Pydantic model that carries all the information about the goal and its history as it moves through the agent's thought process.
-   **Presets:** Reusable "recipes" in the `presets/` folder that define how an agent should behave. They are YAML files that describe the agent's graph of nodes and edges, allowing you to create different workflows (e.g., a simple agent vs. a self-correcting one).
-   **Providers:** The "plugs" that connect AEGIS to different AI backends. This is what makes the framework backend-agnostic.
-   **Executors:** The low-level "drivers" that handle the raw work of talking to services like SSH, Redis, or a web browser. They are built to be robust and reusable.
-   **Tools:** The specific abilities the agent can use, like `run_command` or `save_to_memory`. They are the building blocks of the agent's skills and are designed to be easy for developers to create.

---

## What's Next?

Once you have the framework running, here are a few things you can explore:

-   **Read the Documentation:** Dive into the `docs/` directory to find detailed guides on the architecture, creating new tools, and designing advanced agents.
-   **Explore the UI:** Use the **Graph** tab to visualize how the different agent presets work, and the **Tools** tab to see all the capabilities available to your agent.
-   **Try a Complex Task:** Give the agent a multi-step goal that requires it to use several different tools to see the framework in action.
-   **Create a New Tool:** Follow the developer guide to add a new capability to the agent and expand its skillset.