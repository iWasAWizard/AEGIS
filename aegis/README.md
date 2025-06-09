```markdown
# 🛡️ AEGIS: Autonomous Agentic Framework

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/containerized-Docker-blue)](https://www.docker.com/)
[![Built with LangGraph](https://img.shields.io/badge/built%20with-LangGraph-orange)](https://github.com/langchain-ai/langgraph)

**AEGIS** is a modular, offline-capable, and "air-gapped friendly" autonomous agent framework built on Python and
LangGraph. It leverages local LLMs via Ollama to plan and execute complex, multi-step tasks. Designed as a **Test
Engineer's Swiss Army Knife**, AEGIS acts as a reliable proxy, translating high-level human intent into safe,
repeatable, and auditable technical operations.

The core philosophy is to provide an **idiot-friendly surface** for simple tasks while exposing a **powerful,
configurable engine** for experts.

---

## ✨ Core Features

* **🧠 Autonomous Planning:** Uses a local LLM to reason, plan, and execute tasks step-by-step.
* **🔧 Rich, Modular Toolset:** A comprehensive library of tools for system administration, network diagnostics, file
  operations, web automation, and even fuzzing.
* **🔒 Built for Safety & Auditing:**
    * **Structured History:** Every thought, action, and observation is recorded for full traceability.
    * **Safe Mode:** Tools with potentially dangerous capabilities are gated.
    * **Centralized Executors:** Standardized and reliable execution logic for remote (SSH) and local commands.
* **⚙️ Graph-Based Workflows:** Define complex agent behaviors and logic flows with simple YAML presets using
  LangGraph's power.
* **📦 Air-Gapped & Self-Contained:** Designed to run entirely within a Docker environment with no external internet
  dependencies post-setup.
* **🔌 Dual Interfaces:** Interact via a clean **FastAPI web UI** or a powerful **command-line interface (CLI)**.

## 🏗️ Architecture

The AEGIS architecture is designed for clarity and modularity. It creates a safe abstraction layer between user intent
and system execution.

```

+---------------------------------+
| User Interface |
|      (FastAPI Web UI / CLI)     |
+---------------------------------+
|
v
+---------------------------------+
| AEGIS Launch Endpoint |
| (Parses Request & Loads Config) |
+---------------------------------+
|
v
+---------------------------------+ +--------------------------------+
| Agent Execution Graph |----->| Agent State (TaskState)    |
| (LangGraph: Plan -> Execute ->) | | (Prompt, Config, History, etc) |
+---------------------------------+ +--------------------------------+
|
v
+---------------------------------+ +--------------------------------+
| AEGIS Tool Executor |----->| Tool Registry |
|  (Executes planned tool calls)  | |  (Validates & provides tools)  |
+---------------------------------+ +--------------------------------+
|
v
+---------------------------------+
| Execution Layer |
| (SSH, Local Shell, Browser, etc)|
+---------------------------------+

```

---

## 🚀 Quick Start with Docker (Recommended)

This is the easiest and most reliable way to get AEGIS running.

**Prerequisites:**
*   Docker and Docker Compose installed.
*   An Ollama-compatible LLM pulled locally (e.g., `ollama pull llama3`).

**Steps:**

1.  **Configure Environment:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Open the `.env` file and set `OLLAMA_MODEL` to the model you have downloaded (e.g., `OLLAMA_MODEL=llama3`).

2.  **Build and Run:**
    From the project root, run Docker Compose:
    ```bash
    docker-compose up --build
    ```
    This command will:
    *   Build the AEGIS Docker image, installing all dependencies.
    *   Start the Ollama container.
    *   Start the AEGIS container, which runs the FastAPI server.

3.  **Access the UI:**
    Open your web browser and navigate to `http://localhost:8000`. You should see the AEGIS web dashboard.

---

## 💻 Command-Line Usage

The CLI is perfect for scripted automation and quick tasks.

### 1. Run a Task from YAML

Create a task file, for example `my-task.yaml`:
```yaml
# my-task.yaml
task:
  prompt: "Get the OS version and disk usage from the remote host."
config: "default" # Use the default agent graph
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

---

## 🔧 Extending AEGIS

AEGIS is built to be extended.

### Adding a New Tool

1. Create a new Python file in `aegis/tools/primitives/` or `aegis/tools/wrappers/`.
2. Define a Pydantic model for your tool's input.
3. Write your tool function.
4. Decorate it with `@register_tool` from `aegis.registry`, providing all required metadata.

**Example Template:**

```python
# In aegis/tools/primitives/my_new_tool.py
from pydantic import BaseModel, Field
from aegis.registry import register_tool


class MyToolInput(BaseModel):
    target_host: str = Field(..., description="The host to target.")


@register_tool(
    name="my_new_tool",
    input_model=MyToolInput,
    description="A brief description of what this tool does.",
    category="network",
    tags=["custom", "example"],
    safe_mode=True
)
def my_tool_function(input_data: MyToolInput) -> str:
    # Your tool logic here...
    return f"Tool executed against {input_data.target_host}"
```

AEGIS will automatically discover and register your new tool the next time it starts.

### Creating a New Agent Behavior (Graph)

1. Create a new YAML file in the `presets/` directory (e.g., `my-behavior.yaml`).
2. Define the `state_type`, `entrypoint`, `nodes`, and `edges` for your new graph.
3. You can now launch tasks using this new behavior by specifying its name in an API call or task
   file (`config: "my-behavior"`).

---