```markdown
# 🛡️ AEGIS: Autonomous Agentic Framework

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/containerized-Docker-blue)](https://www.docker.com/)
[![Built with LangGraph](https://img.shields.io/badge/built%20with-LangGraph-orange)](https://github.com/langchain-ai/langgraph)

**AEGIS** is a modular, offline-capable, and "air-gapped friendly" autonomous agent framework built on Python and
LangGraph. It is designed to be the "Cerebral Cortex" in a larger system of systems, using backend intelligence stacks like **BEND** to plan and execute complex, multi-step tasks.

The core philosophy is to provide an **idiot-friendly surface** for simple tasks while exposing a **powerful,
configurable engine** for experts.

---

## ✨ Core Features

*   **🧠 Autonomous Planning:** Uses a local LLM (provided by the **BEND** stack) to reason about problems, form multi-step plans, and select the appropriate tools for the job.
*   **🔧 Rich, Modular Toolset:** A comprehensive library of tools for system administration, network
    diagnostics (`nmap`, `scapy`), security testing (`pwntools`), file operations, web automation (`selenium`), and even
    fuzzing.
*   **🔒 Built for Safety & Auditing:**
    *   **Structured Provenance:** Every task generates a machine-readable `provenance.json` "flight recording" of every
        thought, action, and observation for full traceability.
    *   **Safe Mode:** Restricts the agent to only use tools that cannot perform destructive or state-changing actions.
    *   **Centralized Executors:** Standardized and reliable execution logic for remote (SSH) and local commands.
*   **⚙️ Graph-Based Workflows:** Agent behaviors are defined as graphs using simple YAML presets. This allows for
    creating complex, conditional logic (e.g., "try this, if it fails, do that") without changing Python code.
*   **🔌 Dual Interfaces:** Interact via a clean **React-based web UI** or a powerful **Typer-based command-line
    interface (CLI)**.

---

## 🌟 Advanced Capabilities

Beyond basic tool execution, AEGIS incorporates several advanced systems for enhanced intelligence and usability:

*   **✍️ RAG-Powered Memory:** The agent automatically indexes the logs of every completed task. It can then query this
    memory using the `query_knowledge_base` tool to learn from its own past successes and failures.
*   **✅ Execute-and-Verify Flow:** AEGIS supports advanced workflows (e.g., `verified_flow.yaml`) where the agent not only
    *executes* an action but also runs a follow-up *verification* step. If verification fails, it enters a remediation
    loop to correct the problem autonomously.
*   **🧩 Plugin SDK:** The framework features a complete SDK for creating and managing custom tools. A `plugins/` directory
    allows for drop-in tool loading, and the CLI provides `new-tool` and `validate-tool` commands to streamline
    development.
*   **🗺️ Graph Visualization:** The web UI includes a "Graph" tab that visually renders any agent preset, showing the
    nodes, edges, and conditional logic. This makes complex agent behaviors transparent and easy to debug.

---

## 🏗️ Architecture

AEGIS is designed to be a consumer of a backend intelligence stack like **BEND**.

```
+---------------------------------+
|       BEND Backend Stack        |
| (LLM, STT, TTS, Document RAG)   |
+---------------------------------+
               ^
               | (API Calls)
               v
+---------------------------------+
|          User Interface         |
|      (AEGIS Web UI / CLI)       |
+---------------------------------+
               |
               v
+---------------------------------+      +--------------------------------+
|       Agent Execution Graph     |----->|     Agent State (TaskState)    |
| (LangGraph: Plan -> Execute ->) |<-----| (Prompt, Config, History, etc) |
+---------------------------------+      +--------------------------------+
               |
               v
+---------------------------------+
|        Tool Execution Step      |
|  (Resolves & Validates Tools)   |
+---------------------------------+
```

1.  **Backend Services (BEND):** The BEND stack runs independently, providing LLM inference, voice services, and document storage.
2.  **User Interface (AEGIS):** The user submits a high-level task through the AEGIS Web UI or CLI.
3.  **Agent Execution Graph (AEGIS):** The agent's control loop, powered by LangGraph, uses the LLM from BEND to create a plan.
4.  **Tool Execution (AEGIS):** The agent executes its rich, internal toolset. Some of these tools will make API calls back to BEND to use its services.

---

## 🚀 Quick Start with Docker (Recommended)

AEGIS now requires the **BEND** stack to be running as its backend.

### Prerequisites

1.  **Docker and Docker Compose installed.**
2.  **You have successfully cloned and set up the BEND repository.**

### Steps

1.  **Start the BEND Stack:**
    In a separate terminal, navigate to your BEND repository directory and start its services.
    ```bash
    # In your /path/to/bend/
    ./scripts/switch-model.sh hermes # Select a model for BEND
    docker compose up -d --build
    ```

2.  **Create a Shared Docker Network:**
    This allows the AEGIS and BEND containers to communicate. You only need to do this once.
    ```bash
    docker network create aegis_bend_net
    ```

3.  **Configure BEND to Use the Shared Network:**
    Add the following lines to the end of your `bend/docker-compose.yml` file:
    ```yaml
    networks:
      default:
        name: aegis_bend_net
        external: true
    ```
    Then, restart BEND to apply the network change: `cd bend && docker compose up -d --force-recreate`

4.  **Clone and Configure AEGIS:**
    In another terminal, clone the AEGIS repository.
    ```bash
    git clone https://your-repo-url/aegis.git # Replace with your actual repo URL
    cd aegis
    cp .env.example .env
    ```
    Open `.env` and set any required secrets like `BEND_API_KEY` if you have one configured in BEND.

    **.env.example**
    ```env
    # For AEGIS to communicate with a secured BEND stack
    BEND_API_KEY=your-bend-api-key-if-you-set-one

    # For optional tools that use external APIs (not needed for core AEGIS+BEND)
    # OPENAI_API_KEY=

    # Machine secrets for SSH tools
    ADMIN_PASSWORD=supersecret
    ROOT_PASSWORD=toor
    DEPLOY_PASSWORD=changeme
    ESXI_PASSWORD=vmware123
    ```

5.  **Build and Run AEGIS:**
    From the `aegis` project root, launch the Docker Compose stack.
    ```bash
    docker compose up --build
    ```
    The `wait-for-koboldcpp.sh` script will ensure the AEGIS container waits until BEND's LLM service is ready before starting the API server.

6.  **Access the UI:**
    Open your web browser and navigate to **`http://localhost:8000`**. You should see the AEGIS web dashboard, now powered by the BEND backend.

---

## 💻 Command-Line Usage

The CLI is perfect for scripted automation and quick, targeted tasks.

### Run a Task from a YAML File

Create a task file, for example `my-task.yaml`:

```yaml
# my-task.yaml
task:
  prompt: "Scan localhost for open ports 80, 443, and 8000. Use a TCP Connect scan."
config: "default" # This preset now uses the KoboldCPP backend from BEND
```

Then, run it:

```bash
python -m aegis.cli run-task my-task.yaml
```

### Other Commands

```bash
# List all available tools
python -m aegis.cli list-tools

# Scaffold a new tool in the plugins/ directory
python -m aegis.cli new-tool
```