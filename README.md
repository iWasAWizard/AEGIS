# 🛡️ AEGIS: Autonomous Agentic Framework

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/containerized-Docker-blue)](https://www.docker.com/)
[![Built with LangGraph](https://img.shields.io/badge/built%20with-LangGraph-orange)](https://github.com/langchain-ai/langgraph)

**AEGIS** is a modular, offline-capable, and "air-gapped friendly" autonomous agent framework built on Python and
LangGraph. It leverages local LLMs via **KoboldCPP** to plan and execute complex, multi-step tasks. Designed as a **Test
Engineer's Swiss Army Knife**, AEGIS acts as a reliable proxy, translating high-level human intent into safe,
repeatable, and auditable technical operations.

The core philosophy is to provide an **idiot-friendly surface** for simple tasks while exposing a **powerful,
configurable engine** for experts.

---

## ✨ Core Features

*   **🧠 Autonomous Planning:** Uses a local LLM to reason about problems, form multi-step plans, and select the
    appropriate tools for the job.
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
*   **📦 Air-Gapped & Self-Contained:** Designed to run entirely within a Docker environment with no external internet
    dependencies post-setup. All models and dependencies are local.
*   **🔌 Dual Interfaces:** Interact via a clean **React-based web UI** or a powerful **Typer-based command-line
    interface (CLI)**.

---

## 🌟 Advanced Capabilities

Beyond basic tool execution, AEGIS incorporates several advanced systems for enhanced intelligence and usability:

*   **✍️ RAG-Powered Memory:** The agent automatically indexes the logs of every completed task. It can then query this
    memory using the `query_knowledge_base` tool to learn from past successes and failures, improving its problem-solving
    ability over time.
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

```
+---------------------------------+
|          User Interface         |
|      (FastAPI Web UI / CLI)     |
+---------------------------------+
               |
               v
+---------------------------------+
|      AEGIS Launch Endpoint      |
| (Parses Request & Loads Config) |
+---------------------------------+
               |
               v
+---------------------------------+      +--------------------------------+
|       Agent Execution Graph     |----->|     Agent State (TaskState)    |
| (LangGraph: Plan -> Execute ->) |      | (Prompt, Config, History, etc) |
+---------------------------------+      +--------------------------------+
               |                                        ^
               v                                        |
+---------------------------------+      +--------------------------------+
|        Tool Execution Step      |----->|         Tool Registry          |
|  (Resolves & Validates Tools)   |      |   (Provides Tool Functions)    |
+---------------------------------+      +--------------------------------+
               |
               v
+---------------------------------+
|         Execution Layer         |
| (SSH, Local Shell, Browser, etc)|
+---------------------------------+
```

1.  **User Interface:** The user submits a high-level task through the Web UI or the CLI.
2.  **Launch Endpoint:** The request is received, a configuration preset (e.g., `default.yaml`) is loaded, and the
    initial `TaskState` is created.
3.  **Agent Execution Graph:** The state is passed to a `LangGraph` instance, which controls the agent's main loop (
    e.g., `Plan -> Execute -> Verify -> Loop`). The planning steps involve LLM calls to **KoboldCPP**.
4.  **Tool Execution:** When the agent decides to use a tool, it calls the `Tool Registry`, which provides the validated
    tool function and its input schema.
5.  **Execution Layer:** The tool's logic is executed through a standardized primitive, such as the `SSHExecutor` or a
    local `subprocess` call.
6.  **State Update:** The result of the tool's execution is recorded in the `TaskState` history, and the loop continues
    until a termination condition is met.

---

## 🚀 Quick Start with Docker (Recommended)

This is the easiest and most reliable way to get AEGIS running with all its dependencies.

### Prerequisites

1.  **Docker and Docker Compose installed.**
2.  **LLM Model File (GGUF or EXL2 format):**
    *   AEGIS uses **KoboldCPP** as its local LLM backend. You need to download a compatible model file.
    *   **Recommended Source:** [Hugging Face Hub](https://huggingface.co/models). Search for GGUF models from creators like "TheBloke".
    *   **Example (Llama 3 8B Instruct):**
        *   Search for "TheBloke Llama-3-8B-Instruct-GGUF".
        *   Download a specific quantization, for example: `Llama-3-8B-Instruct.Q5_K_M.gguf`
    *   **Example (Mistral 7B Instruct):**
        *   Search for "TheBloke Mistral-7B-Instruct-v0.2-GGUF".
        *   Download: `mistral-7b-instruct-v0.2.Q4_K_M.gguf`
    *   Ensure the model you choose is compatible with the version of KoboldCPP used in the Docker image.

### Steps

1.  **Clone the Repository:**
    ```bash
    git clone https://your-repo-url/aegis.git # Replace with your actual repo URL
    cd aegis
    ```

2.  **Prepare Model Directory and `.env` File:**
    *   Create a directory to store your downloaded LLM files. This directory will be mounted into the KoboldCPP Docker container.
        ```bash
        mkdir koboldcpp-models
        ```
    *   Move your downloaded `.gguf` (or `.exl2`) model file(s) into this `koboldcpp-models` directory. For example:
        ```bash
        mv ~/Downloads/Llama-3-8B-Instruct.Q5_K_M.gguf ./koboldcpp-models/
        ```
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Open the newly created `.env` file and **set `KOBOLDCPP_MODEL` to the exact filename of the model you placed in `koboldcpp-models`**. For example:
        ```dotenv
        # .env (snippet)
        KOBOLDCPP_MODEL=Llama-3-8B-Instruct.Q5_K_M.gguf
        KOBOLDCPP_API_URL="http://koboldcpp:5001/api/v1/generate"

        # Optional: Adjust KoboldCPP startup parameters (used by docker-compose.yml)
        CONTEXT_SIZE=4096
        # LAYERS=33 # Number of layers to offload to GPU (0 for CPU only)
        # THREADS=8 # Number of CPU threads for KoboldCPP
        ```
        You can also configure machine passwords and other settings in this `.env` file.

3.  **Build and Run with Docker Compose:**
    From the project root, launch the Docker Compose stack:
    ```bash
    docker-compose up --build
    ```
    This command will:
    *   Build the AEGIS Docker image, installing all Python and system dependencies.
    *   Start the KoboldCPP container. The `command` in `docker-compose.yml` will use the `KOBOLDCPP_MODEL` environment variable to load your specified model from the mounted `/models` volume (which corresponds to your local `koboldcpp-models` directory).
    *   Start the AEGIS container, which runs the FastAPI server.
    *   **Note:** The first time KoboldCPP loads a large model, it might take a few minutes. Monitor the logs using `docker-compose logs -f koboldcpp`.

4.  **Access the UI:**
    Once KoboldCPP has loaded the model and AEGIS has started (see `docker-compose logs -f agent`), open your web browser and navigate to **`http://localhost:8000`** (or your `AEGIS_HOST`:`AEGIS_PORT` if changed). You should see the AEGIS web dashboard.

---

## 💻 Command-Line Usage

The CLI is perfect for scripted automation and quick, targeted tasks.

### 1. Run a Task from a YAML File

This is the most powerful way to use the CLI. Create a task file, for example `my-task.yaml`:

```yaml
# my-task.yaml
task:
  prompt: "Scan localhost for open ports 80, 443, and 8000. Use a TCP Connect scan. Verify the result by checking if the output contains '8000/tcp open', then finish with a status of success."
# Use the advanced verification and remediation graph
config: "verified_flow" # This preset is now configured to use KoboldCPP
execution:
  iterations: 5 # Set a max of 5 steps for this task
```

Then, run it with the `run-task` command:

```bash
python -m aegis.cli run-task my-task.yaml
```

### 2. List Available Tools

To see all the tools the agent can use, run:

```bash
python -m aegis.cli list-tools
```

### 3. Create and Validate a New Tool

Use the built-in scaffolder and validator to extend the agent's capabilities:

```bash
# Interactively create a new tool boilerplate in the plugins/ directory
python -m aegis.cli new-tool

# Validate your new tool file for syntax and metadata errors
python -m aegis.cli validate-tool plugins/my_new_tool.py
```

---

## 🔧 Extending AEGIS

AEGIS is built to be extended.

### Adding a New Tool

1.  Use the `new-tool` CLI command to generate a complete boilerplate file in the `plugins/` directory.
    ```bash
    python -m aegis.cli new-tool
    ```
2.  Open the newly generated file (e.g., `plugins/my_new_tool.py`) and implement your logic in the function body. The
    Pydantic input model and decorator are already set up for you.
3.  Restart the AEGIS application. The tool loader will automatically discover and register your new tool.

### Creating a New Agent Behavior (Graph)

1.  Create a new YAML file in the `presets/` directory (e.g., `my-behavior.yaml`).
2.  Define the `state_type`, `entrypoint`, `nodes`, and `edges` for your new graph. You can use `default.yaml`
    and `verified_flow.yaml` (which are now KoboldCPP-centric) as templates.
3.  You can now launch tasks using this new behavior by specifying its name in an API call or task
    file (`config: "my-behavior"`).
```