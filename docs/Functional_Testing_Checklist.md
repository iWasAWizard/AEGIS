# Functional Testing Checklist
This list outlines the core functions of the combined AEGIS and BEND system.
### Testing Legend

-   **Unit Test:** An automated test for a single function or class in isolation. Most of these should already exist in our `tests/` directory.
-   **Integration Test:** An automated test that verifies the interaction between a few components (e.g., an agent step calling the tool registry).
-   **End-to-End (E2E) Test:** A full run of the system, usually driven by a regression test file, that verifies all components work together to achieve a goal.
-   **Manual Test:** A hands-on test performed by an operator using the UI or CLI to verify functionality that is difficult to automate.

---

### ✅ BEND Stack: Operational Validation Checklist

This ensures the entire intelligence backend is stable and performing as expected.

| Action to Validate | How to Test | What to Look For |
| :--- | :--- | :--- |
| **Stack Management** | Manual | Run `./scripts/manage.sh up`, `down`, `status`, and `restart`. |
| **GPU Acceleration** | Manual | Run `./scripts/manage.sh up --gpu` and check `nvidia-smi` in another terminal to confirm processes are on the GPU. |
| **Model Switching** | Manual | Run `./scripts/switch-model.sh <model_key>` and inspect the `.env` file to confirm `MODEL_NAME` and `KOBOLDCPP_MODEL_NAME` are updated. |
| **Service Health** | Manual | Run `./scripts/manage.sh healthcheck`. All key services (`vLLM`, `Guardrails`, etc.) must report `[ OK ]`. |
| **vLLM API Endpoint** | Manual | Use `curl` or a tool like Postman to send a chat completion request to `http://localhost:12011/v1/chat/completions`. |
| **KoboldCPP API Endpoint**| Manual | Use `curl` to send a `/generate` request to `http://localhost:12009/api/generate`. |
| **RAG Ingestion & Retrieval**| Manual | Use `curl` to `POST` a document to `/ingest` and then retrieve it with `/retrieve` on port `12007`. |
| **Redis Memory Service** | Manual | Use a Redis client (`redis-cli`) to connect to `localhost:12010` and perform `SET` and `GET` commands. |

---

### ✅ AEGIS: Core Engine & Agent Logic Checklist

This validates the agent's "brain" and its ability to reason, plan, and self-correct.

| Core Function | How to Test | What to Look For |
| :--- | :--- | :--- |
| **Configuration Loading** | Unit Test | The `config validate` CLI command should pass. This validates all presets, backends, and machines. |
| **Planning (`reflect_and_plan`)**| Integration Test | Verify it generates a valid `AgentScratchpad`. Check that a `tool_allowlist` in a preset correctly filters the tools shown to the LLM. |
| **Tool Execution (`execute_tool`)**| Integration Test | Verify it correctly handles: a) successful tool runs, b) `ToolNotFoundError`, c) `ValidationError` (bad args), and d) `ToolExecutionError`. |
| **Guardrails Integration**| Integration Test | Verify that a plan to run a dangerous command (e.g., `rm -rf`) is caught and blocked by the `_check_guardrails` function in `execute_tool`. |
| **State Transition Logic** | E2E Test | Run a multi-step task. Check the provenance report to ensure the graph correctly loops from `execute` back to `plan`. |
| **Verification Loop** | E2E Test | Run the `verified_flow` preset. Cause a tool to fail and verify the agent routes to `remediate_plan` and successfully recovers. |
| **Human-in-the-Loop** | E2E Test | Run the `human_in_the_loop` preset with a tool like `ask_human_for_input`. Verify the task status returns `PAUSED`. |
| **Agentic MoE** | E2E Test | Run the `orchestrator` preset. Verify it successfully calls `dispatch_subtask_to_agent` and that a sub-agent runs and returns a result. |

---

### ✅ AEGIS: Tool & Executor Layer Checklist

This ensures the agent's "hands" are working correctly.

| Action to Validate | How to Test | What to Look For |
| :--- | :--- | :--- |
| **All Tool Registrations** | Unit Test | The `tool validate <path>` command should pass for every single tool file in the repository. |
| **Local Filesystem Tools** | Unit Test | Verify `write_to_file`, `read_file`, and `delete_file` work as expected. |
| **Remote Filesystem Tools**| Unit Test | Verify `read_remote_file`, `append_to_remote_file`, etc., correctly call the `SSHExecutor`. |
| **Command Execution Tools**| Unit Test | Verify `run_local_command` and `run_remote_command` execute commands and capture output. |
| **Network Tools** | Unit Test | Verify tools like `check_port_status` return expected results. |
| **Data Tools** | Unit Test | Verify `extract_structured_data` correctly calls Instructor and `diff_text_blocks` produces a correct diff. |
| **Memory Tools** | Unit Test | Verify `save_to_memory` and `recall_from_memory` correctly call the `RedisExecutor`. |

---

### ✅ AEGIS: User Interface & Experience Checklist

This validates the two primary ways operators will interact with the system.

| Interface | Action to Validate | How to Test |
| :--- | :--- | :--- |
| **Web UI** | **Task Launch:** Can you successfully launch a task using `vllm_local`? | Manual |
| | **HITL Flow:** Can you launch a task with the `human_in_the_loop` preset, see the "PAUSED" UI, submit feedback, and see the task complete? | Manual |
| | **Log Streaming:** Do live logs appear in the right-hand panel during a task run? | Manual |
| | **Admin Tab:** Do the `Validate Configs` and `Create New Tool` buttons work and show a status message? | Manual |
| | **Other Tabs:** Do the `Tools`, `Artifacts`, and `Presets` tabs correctly load and display their data? | Manual |
| **Interactive Shell** | **Shell Startup:** Does `python -m aegis` launch the `(aegis) >` shell without errors? | Manual |
| | **Task Execution:** Does `task run <file.yaml>` successfully execute an agent run? | Manual |
| | **Informational Commands:** Do `tool list`, `preset list`, and `artifact list` work and display correct tables? | Manual |
| | **Developer Commands:** Do `config validate` and `tool new` work as expected from the shell? | Manual |