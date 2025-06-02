# 🧠 Agentic LLM: Autonomous LangGraph Task Agent

This project is a fully modular, airgap-safe, LangGraph-powered autonomous agent that uses a local LLM (via Ollama) to plan, execute, and evaluate complex tasks across multiple VMs.

---

## 🚀 Features

- ✅ Autonomous multi-step task planning via LangGraph
- 🧠 Ollama local LLM backend (GGUF or EXL2)
- 🖥️ QEMU & VMware VM support (power, snapshot, guest execution)
- 📄 Test procedure CSVs + Markdown reports + full JSON logs
- 🧪 Test Coverage Mode: actual vs expected validation
- 🔁 Execution timeline chart per run
- 🌐 Web dashboard with task launcher, live logs, and queue support
- 📂 Machine manifest describes every available VM and its capabilities

---

## 📦 Quick Start

### Option 1: Run Manually (Ollama must be running)

```bash
# Run the main web agent manually
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

## 🛠️ Project Layout

```
agentic_agent/
├── agents/
├── tools/
├── utils/
├── web/
├── run_agent_web.py
├── run_dashboard.py
examples/
reports/
```

---

## 🧰 Machine Manifest Format

Edit `machines.yaml` to define your virtual infrastructure:

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

## 🧪 Reports

Every run produces:
- `report.md`: human-readable summary
- `record.json`: full machine-readable trace
- `procedure.csv`: structured test steps
- `timeline.png`: execution bar chart

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

For more examples, see `examples/README.md`
