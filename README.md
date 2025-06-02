# 🧠 AEGIS: Autonomous LangGraph Task Agent + Modular Execution Framework

![Docker](https://img.shields.io/badge/containerized-Docker-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)


AEGIS is a fully modular, airgap-safe, LangGraph-powered autonomous agent that uses a local LLM (via Ollama) to plan, execute, and evaluate complex tasks across multiple VMs. It combines graph-based agent execution with a robust modular tooling system, safe-mode enforcement, structured logging, and a fully containerized API.

---

## 🚀 Features

- ✅ Autonomous multi-step task planning via LangGraph
- 🧠 Local LLM backend via Ollama (GGUF or EXL2)
- 🖥️ QEMU & VMware VM support (power, snapshot, guest execution)
- 📄 Test procedure CSVs + Markdown reports + full JSON logs
- 🔁 Execution timeline chart per run
- 🧪 Test Coverage Mode: actual vs expected validation
- 🌐 Web dashboard with task launcher, live logs, and queue support
- 📂 Machine manifest (`machines.yaml`) defines all known virtual hosts
- 🔧 Modular tool system with registry enforcement, Pydantic schemas, safety validation
- 🧱 CLI and HTTP API interfaces
- 🛡️ Safe mode, timeout, retry, category tagging, and structured runtime reports

---

## 🏗️ Architecture

```
User/HTTP/CLI
     ↓
Preset YAML (Graph + Task Prompt)
     ↓
Agent Runner (LangGraph-based FSM)
     ↓
 Tool Registry —> Validated Tool Call
     ↓
 Tool (Primitive/Wrapper)
     ↓
System/VM/LLM/Shell/Filesystem/Browser
```

---

## 📦 Quick Start

### Option 1: Run Manually (Ollama must be running)

```bash
OLLAMA_HOST=http://localhost:11434 python aegis/run_agent_web.py --task "check disk usage"
```

### Option 2: Use Docker Compose (Recommended)

```bash
docker compose up --build
```

This will:
- Start the Ollama daemon (ollama/ollama container)
- Build and run the autonomous agent
- Launch the web dashboard at http://localhost:8000

---

## 🧳 Example Tasks

```bash
python aegis/run_agent_web.py --task "check memory usage"
```

Or define a queue:

```yaml
# tasks.yaml
- task: "check disk usage on all Linux VMs"
  safe_mode: true
```

Then run:

```bash
python aegis/run_agent_web.py --queue tasks.yaml
```

---

## 📁 Project Layout

```
aegis/
├── agents/                  # Agent logic and LangGraph config
├── tools/                   # Primitives, wrappers, integrations
├── utils/                   # Helpers, timeline, reporting
├── run_agent_web.py         # Agent runner entry point
├── serve_dashboard.py       # FastAPI HTTP interface
├── presets.yaml             # Default LangGraph workflows
├── machines.yaml            # VM manifest file
├── registry.py              # Tool validation & runtime enforcement
docker-compose.yml           # Containerized entrypoint
```

---

## 🧰 Machine Manifest Format

```yaml
machines:
  ubuntu-lab:
    platform: qemu
    shell: bash
    vm_name: ubuntu-lab
    control_tool: qemu_guest_exec
    credentials:
      guest_user: root
      guest_password: hunter2

  windows-sandbox:
    platform: vmware
    shell: powershell
    vm_name: WIN10-SEC-LAB
    control_tool: vmware_guest_exec
    vcenter:
      host: vcenter.local
      user: agent
      password: vmwareagent123
    credentials:
      guest_user: Administrator
      guest_password: P@ssword!
```

---

## 🧠 Tool Model

AEGIS supports both:
- **Primitive tools**: atomic filesystem/network/shell/VM operations
- **Wrapper tools**: composition, orchestration, or external integrations

Each tool must be registered with:
- `name`
- `description`
- `input_model` (Pydantic)
- `tags`, `categories`
- `safe_mode`, `retry`, `timeout`

Tools are loaded automatically at runtime and validated via the `registry.py`.

---

## 🧪 Reports

Every run produces:
- `report.md`: human-readable summary
- `record.json`: full machine-readable trace
- `procedure.csv`: structured test steps
- `timeline.png`: execution bar chart

---

## 🧩 API Endpoints

- `POST /launch`: Launch a task with a preset and task prompt
- `GET /health`: Confirm server readiness
- `GET /status`: (coming soon) Query current task state

---

## 🛡️ Safe Mode & Validation

- All tools run in `safe_mode` unless explicitly marked otherwise
- Tools with system/shell/LLM-level control are gated or sandboxed
- Graphs are validated for integrity before runtime
- Execution context is logged and checkpointed

---

## 💡 Extend the System

- Add tools under `tools/`
- Define presets via `presets.yaml`
- Extend machine definitions via `machines.yaml`
- Add queue entries via `tasks.yaml`
- Enable fuzzing, browser interaction, or VM coordination using wrappers

---

## 📄 RVTM & Test Coverage

This project includes a full Requirements Verification Traceability Matrix (RVTM) for auditing and test coverage purposes. See `/docs/` or `/rvtm/` for details.

---


---

## 🧪 Development Commands

```bash
# Run tests
pytest

# Lint with Ruff
ruff check aegis/

# Format with Black
black aegis/
```

---

## 🧰 Tool Template (Primitive)

```python
from pydantic import BaseModel
from aegis.registry import register_tool

class EchoInput(BaseModel):
    message: str

@register_tool(name="echo_message", input_model=EchoInput, tags=["debug"], safe_mode=True)
def run(input: EchoInput) -> str:
    return input.message
```

Place this in `tools/primitives/echo.py` and it will be automatically registered.

---

## 📋 Requirements Traceability

A full RVTM (Requirements Verification Traceability Matrix) is available to verify system correctness and test coverage.

📄 [View the RVTM →](docs/AEGIS_RVTM.md)

---
