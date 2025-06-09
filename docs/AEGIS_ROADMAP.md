# 🛡️ AEGIS: Consolidated Feature Roadmap

This document serves as the ground truth for the future development of the AEGIS framework. It combines the original v2
roadmap with new strategic ideas, providing a clear vision for the next generation of AEGIS capabilities.

---

## `Category 1: 🧠 Core Intelligence & Autonomy`

*These features focus on making the agent smarter, more context-aware, and more autonomous in its problem-solving.*

### **1.1. Goal-Oriented Persistent Agents**

* **Description:** Shift the agent's role from a one-off "task runner" to a long-running "goal maintainer." Instead of a
  single prompt, the agent is given a persistent invariant to maintain (e.g., "Ensure the web service on host X is
  always responsive"). The agent then runs in an indefinite loop, monitoring the state and taking corrective action only
  when the goal is violated.
* **Why It Matters:** This elevates AEGIS from a task execution engine to a true autonomous system operator, enabling
  self-healing infrastructure, continuous compliance monitoring, and "fire-and-forget" reliability.
* **Implementation Sketch:**
    1. **New Entry Point:** A `aegis run --persistent` command and corresponding API endpoint.
    2. **Stateful Graph:** The graph's termination logic is replaced with a `check_goal_met` node, which loops back to
       a "wait" or "sleep" node on success, creating a continuous monitoring cycle.

### **1.2. "Finishing School" for Tool Usage**

* **Description:** Create a system to fine-tune the agent's planning model specifically on high-quality examples of its
  own successful tool usage.
* **Why It Matters:** This directly tackles the "last mile" problem of LLM reliability. General-purpose models are great
  at reasoning but can be poor at remembering the precise JSON syntax for tool arguments. A specialized, fine-tuned
  model would be far more reliable and require fewer remediation loops for simple errors.
* **Implementation Sketch:**
    1. **Dataset Generation:** A script to parse the `provenance.json` reports from successful runs, creating a dataset
       of `(goal + history, successful_tool_plan)` pairs.
    2. **Fine-Tuning Pipeline:** A script using a library like `unsloth` or `axolotl` to fine-tune a base model on the
       generated dataset.
    3. **Specialized Planner Model:** The resulting model (e.g., `aegis-planner:1.0`) can be configured as the default
       planner, improving core reliability.

### **1.3. "Cost-Aware" Planning & Resource Limiting**

* **Description:** Make the agent aware of the "cost" (e.g., time, risk, API credits) of its actions. The planner would
  be prompted to find the most efficient path to a goal within a given resource budget.
* **Why It Matters:** This introduces a layer of pragmatism and efficiency crucial for real-world deployment where
  resources are not infinite. It prevents the agent from choosing overly "expensive" actions when a cheaper alternative
  exists.
* **Implementation Sketch:**
    1. **Cost Metadata:** Add optional `cost: int` and `risk: int` fields to the `ToolEntry` schema in the registry.
    2. **Prompt Engineering:** The planner's prompt will include this metadata in tool descriptions and be given an
       overall budget to manage.
    3. **State Tracking:** `TaskState` will track `cumulative_cost`, and the termination logic will end the task if the
       budget is exceeded.

---

## `Category 2: 🌐 Distributed & Collaborative Systems`

*These features focus on expanding AEGIS from a single agent to a coordinated multi-agent or multi-machine system.*

### **2.1. Agent-to-Agent Coordination**

* **Description:** Enable one AEGIS agent to delegate a sub-task to another agent, potentially running on a different
  machine.
* **Why It Matters:** This allows for specialization and scalability. A "manager" agent can decompose a complex problem
  and dispatch tasks to specialized "worker" agents (e.g., a database agent, a security agent).
* **Implementation Sketch:**
    1. **Agent Registry:** A service where agents can register their availability, location, and capabilities.
    2. **`dispatch_task_to_agent` Tool:** A new tool that makes a remote API call to another agent's `/launch` endpoint
       and waits for the result.
    3. **DAG of Agents:** Build workflows where the completion of one agent's task can trigger another, creating a
       distributed system of collaborating specialists.

### **2.2. Live Environment State Cache (The "Digital Twin")**

* **Description:** Maintain a near real-time, structured, in-memory model of a target machine's state (processes, ports,
  services). The agent consults this cache before running new discovery tools.
* **Why It Matters:** Massively improves efficiency by reducing redundant "sensor" tool calls. It provides the planner
  with structured, immediate context, leading to smarter, more direct plans.
* **Implementation Sketch:**
    1. **Cache in `TaskState`:** Add an `environment_cache: Dict` field to the `TaskState` object.
    2. **`update_environment_cache` Node:** A dedicated graph node runs a battery of sensor tools at the start of an
       execution loop to populate this cache.
    3. **Prompt Injection:** The planner prompt is enhanced to include a summary of this cache, giving the LLM
       immediate, structured data about the target environment.

### **2.3. Dynamic Inventory Provider System**

* **Description:** Overhaul the static `machines.yaml` file by replacing it with a pluggable "Inventory Provider"
  system. AEGIS could then fetch its list of target machines dynamically from various sources.
* **Why It Matters:** The static YAML file is a bottleneck in dynamic, large-scale environments. This allows AEGIS to
  integrate directly with cloud providers (AWS, Azure), CMDBs, or virtualization platforms (Proxmox, vCenter), making it
  vastly more scalable.
* **Implementation Sketch:**
    1. **`InventoryProvider` Interface:** Define a standard class with methods like `get_machine(name)`
       and `list_machines()`.
    2. **Implementations:** Create concrete classes for different
       sources (`YamlInventoryProvider`, `AwsEc2InventoryProvider`, `AnsibleInventoryProvider`, etc.).
    3. **Configuration:** A new section in `config.yaml` will specify which provider to use and its credentials.

---

## `Category 3: 🛠️ Framework & Developer Experience`

*These features focus on improving the core engine, extensibility, and the developer/operator workflow.*

### **3.1. Modular Execution Engine**

* **Description:** Abstract the core graph runner (currently LangGraph) to allow different execution backends to be
  plugged in.
* **Why It Matters:** This future-proofs the framework, allowing for non-LLM backends (like a simple DAG runner for
  pre-defined scripts) or different agent architectures (like a Finite State Machine) without rewriting the tool system.
* **Implementation Sketch:**
    1. **Pluggable `AgentGraph`:** Refactor the `AgentGraph` class to be an interface that different runner
       implementations can satisfy.
    2. **Alternative Backends:** Implement new runners like `YamlDagRunner` for simple, scripted task execution.

### **3.2. Human-in-the-Loop (HITL) Intervention**

* **Description:** Allow the agent to explicitly pause its execution and ask a human for clarification or confirmation,
  especially before executing high-risk actions.
* **Why It Matters:** This builds operator trust, safely resolves ambiguity, and provides a critical guardrail for
  potentially destructive operations. It turns the user from a spectator into a collaborator.
* **Implementation Sketch:**
    1. **`ask_human` Tool:** A special tool that pauses the graph's execution when called.
    2. **Pause/Resume API:** The tool call updates the task status. The UI displays the agent's question and allows the
       user to submit an answer via a `/resume` API endpoint.
    3. **State Injection:** The user's response is injected back into the graph as the `observation` from
       the `ask_human` tool, allowing the agent to continue with new information.

### **3.3. Dynamic Tool Generation**

* **Description:** An advanced capability where the agent can write, validate, and register its own tools at runtime to
  solve novel problems.
* **Why It Matters:** This represents a significant leap in autonomy. The agent is no longer limited by its pre-defined
  toolset and can create its own solutions on the fly.
* **Implementation Sketch:**
    1. **New Tools:** A `generate_python_code` tool and an internal `hot_reload_tools` tool.
    2. **Workflow:** The agent recognizes a missing capability, uses `generate_python_code` to write a new tool to
       a `plugins/` file, validates it with `run_local_command("aegis validate-tool ...")`, and then
       uses `hot_reload_tools` to make it available for the next step.

---

## `Category 4: 📊 UI & Auditing`

*These features focus on improving the operator's ability to monitor, understand, and audit the agent's behavior.*

### **4.1. Rich Web UI Enhancements**

* **Description:** Expand the FastAPI frontend into a more comprehensive and interactive operator dashboard.
* **Why It Matters:** A powerful visual interface makes the agent's complex internal state transparent and accessible,
  facilitating monitoring, debugging, and control.
* **Implementation Sketch:**
    1. **Graph-based Task View:** A real-time visualization of the execution graph, highlighting the currently active
       node.
    2. **Interactive Preset Editor:** A form-based UI for creating and editing `preset.yaml` files with schema-backed
       validation and hints.

### **4.2. Autonomous Red Teaming & Security Posture Assessment**

* **Description:** Give the agent a high-level security objective (e.g., "Find vulnerabilities in host Y") and have it
  autonomously use its security tools to generate a penetration test report.
* **Why It Matters:** This is a perfect "capstone" feature that demonstrates the synergy between AEGIS's autonomous
  planning and its security-focused toolset.
* **Implementation Sketch:**
    1. **`red_team.yaml` Preset:** A new graph designed for an `Explore -> Probe -> Report` loop.
    2. **CVE-Informed RAG:** The agent's knowledge base can be pre-loaded with vulnerability information, which it
       queries after discovering services on a target.
    3. **Custom Report Generation:** The `summarize_result` step would be customized to format the final output as a
       structured security report.

### **4.3. "Rehearsal Mode" & Plan Visualization**

* **Description:** A "dry run" mode where the agent generates its entire multi-step plan before execution. The operator
  can then review and approve this plan.
* **Why It Matters:** This is the ultimate safety and predictability feature, allowing a human to sanity-check the
  agent's logic before any actions are taken in a critical environment.
* **Implementation Sketch:**
    1. **`rehearse` Mode:** A launch mode where the `execute_tool` step is replaced with a mock that returns plausible
       example outputs.
    2. **`plan.json` Artifact:** The full sequence of proposed steps is saved as a new artifact.
    3. **UI Visualization:** The UI can load this `plan.json` and render it as a step-by-step flowchart, with an "
       Approve" button to trigger the live run.