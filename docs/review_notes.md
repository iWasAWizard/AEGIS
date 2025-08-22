# What’s solid (nice bones)

* **LangGraph-style loop & steps present**: `reflect_and_plan`, `execute_tool`, `summarize_result`, `verification`, `check_termination` with a `TaskState` container. (See `aegis/agents/agent_graph.py`, `aegis/agents/steps/*`.)
* **Tooling architecture**: decorator-based **tool registry** + typed input models; plugins for Docker/Slack/GitLab; executor layer (SSH, local, http, selenium, scapy, pwntools, docker).
  Paths: `aegis/registry.py`, `plugins/*.py`, `aegis/executors/*.py`
* **Backend abstraction** with providers (Ollama, vLLM, OpenAI, Koboldcpp, replay).
  Paths: `aegis/providers/*`, `aegis/utils/llm_query.py`
* **HITL hooks** exist: `process_human_feedback` step and a preset wired for HITL.
  Paths: `aegis/agents/steps/interaction.py`, `presets/human_in_the_loop_test.yaml`
* **Observability scaffolding**: replay logger, provenance scaffold, artifact manager, structured history entries.
  Paths: `aegis/utils/replay_logger.py`, `aegis/utils/provenance.py`, `aegis/utils/artifact_manager.py`
* **Configs/presets**: agent graphs for network/red team/QA/orchestrator; global defaults with iteration cap + LLM timeouts.
  Paths: `presets/*.yaml`, `config.yaml` (iterations, planning timeout)

# Gaps & concrete fixes (prioritized)

## 1) Dry-run & determinism (critical)

**What I didn’t find:** a runtime “simulate/no-op” switch or deterministic controls exposed to the loop.

* Add fields to `aegis/schemas/runtime.py` (or your settings) like:

  * `dry_run: bool`, `max_steps: int`, `wall_clock_timeout_s: int`, `temperature`, `top_p`, `seed`.
* In `aegis/agents/steps/execute_tool.py`: short-circuit tool calls if `dry_run`—emit a **preview** history entry and skip execution. Also enforce `max_steps` and wall-clock budget in `check_termination.py`.

**Where to wire:**
`aegis/agents/steps/execute_tool.py`, `aegis/agents/steps/check_termination.py`, `aegis/schemas/runtime.py`, `config.yaml (defaults.*)`

## 2) Tool I/O contracts, error taxonomy, and validators (critical)

You’ve got the decorator registry and Pydantic inputs—great. What’s missing is **strict output shape + error taxonomy + auto-repair**:

* Define a **ToolResult** dataclass (or Pydantic) with:

  * `ok: bool`, `stdout: str | bytes_ref`, `stderr: str`, `exit_code: int | None`, `error_type: Literal["Timeout","Auth","NotFound","Parse","PolicyDenied","Runtime"] | None`, `redactions_applied: list[str]`, `latency_ms: int`.
* In `execute_tool.py`, wrap every tool call:

  * Catch exceptions → normalize into `ToolResult(ok=False, error_type=..., stderr=...)`.
  * Attach **target host/interface labels** (see §3).
* Add **programmatic validators** before the LLM “verification” step:

  * Example: for `docker_list_containers`, assert JSON parses and array entries have `id/name/state`; for `ssh_exec`, assert exit\_code==0 unless policy allows nonzero.

**Where to wire:**
`aegis/agents/steps/execute_tool.py`, `aegis/registry.py` (enforce output schema), `aegis/utils/validation.py` (validator helpers)

## 3) Multi-NIC machine manifests + per-interface ACLs (critical)

Right now `aegis/schemas/machine.py` + `machines.yaml` model a single `ip`. Your use case needs multi-interface selection and policy:

**Schema (add fields):**

```yaml
machines:
  - name: saturn-03
    roles: [collector, linux]
    auth_profile: linux_std
    interfaces:
      - name: mgmt0
        ipv4: 10.10.3.41/24
        gateway: 10.10.3.1
        vlan: 30
        tags: [mgmt, ssh]
      - name: test1
        ipv4: 172.20.6.41/24
        vlan: 206
        tags: [test, high-throughput]
      - name: oob
        ipv4: 192.168.100.41/24
        tags: [oob, ipmi]
    acls:
      allow_tools:
        - cmd.exec: [mgmt0, test1]
        - files.pull: [mgmt0]
        - power.cycle: [oob]      # requires approval
```

* Update `aegis/schemas/machine.py` and `aegis/utils/machine_loader.py` to emit a **resolved interface map** and a helper `select_interface(tags=["mgmt"])`.
* In `execute_tool.py`, **bind tool execution to an interface**; reject if not permitted by `acls`.

**Where to wire:**
`aegis/schemas/machine.py`, `aegis/utils/machine_loader.py`, and every executor that targets hosts (SSH, HTTP, scapy) to accept `interface` metadata.

## 4) Policy engine & circuit breakers (critical)

I see guardrail mentions in code and docs, but not an explicit **action policy** layer:

* Create a **policy check** in `execute_tool.py` *before* any tool runs:

  * Inputs: `{actor, tool_name, target_machine, interface, time, args}`.
  * Output: `ALLOW | REQUIRE_APPROVAL | DENY`.
* Add **rate limits/quotas** per tool (e.g., “ssh\_exec: 10/min per machine”) and a **circuit breaker** (N consecutive failures → trip for M minutes → escalate to human).
* Expose a **“policy simulate”** path so the planner can ask “Would this be allowed?” during `reflect_and_plan`.

**Where to wire:**
`aegis/agents/steps/execute_tool.py` (pre-flight), `aegis/utils/validation.py` (policy helpers), `docs/policies.md` (matrix)

## 5) HITL approvals with preflight diffs (high)

You’ve got `process_human_feedback` and a preset—great. Make it operational:

* Add a **preflight renderer** that assembles: action, targets, *exact commands*, expected side-effects, file diffs (when applicable), **blast radius**, and **rollback plan**.
* Gate risky tools (reboots, firewall/apply config, power) behind `REQUIRE_APPROVAL`.
* Default **HITL=on** for unknown networks.

**Where to wire:**
`aegis/agents/steps/interaction.py` (feedback flow), `presets/human_in_the_loop_test.yaml` (edges back to plan), UI side to show preview.

## 6) Loop/degeneracy & wall-clock guard (high)

You have iterations in `config.yaml`, but add:

* **Duplicate-action detector** (same tool+args against same target ≥K times in L steps) → trigger reflexive rethink or halt.
* **Wall-clock budget** per run; terminate with a crisp status in provenance.

**Where to wire:**
`aegis/agents/steps/check_termination.py`, `aegis/utils/replay_logger.py`

## 7) Self-critique / verification pass (high)

You’ve got `verification.py` scaffolding. Make it bite:

* Programmatic validators run first. If they fail → feed a **structured failure** into `VerificationJudgement` prompt (“Expected X, saw Y; hypothesis?”) and allow exactly **one** self-repair step.
* If still failing → escalate or halt per policy.

**Where to wire:**
`aegis/agents/steps/verification.py`, `aegis/utils/validation.py`

## 8) Provenance: hash-chained run ledger + artifact manifests (high)

You’ve started `provenance.py` and `artifact_manager.py`. Make it tamper-evident:

* Every step writes `{run_id, step_id, utc_ts, tool, args_hash, target_host, interface, result_hash, parent_step}` and computes a **hash chain** (`prev_hash` → `curr_hash`).
* Every saved artifact writes a manifest `{sha256, size, source_host, path, collected_by_step, mime}`.
* Roll these into a **final JSON report** with status and durations.

**Where to wire:**
`aegis/utils/provenance.py`, `aegis/utils/artifact_manager.py`, `aegis/utils/replay_logger.py`

## 9) Model capability flags & fallbacks (med)

You’ve got providers + model selection. Add **capability metadata**:

* In your model manifest/backends: `json_mode`, `function_calling`, `ctx_window`, `max_output_tokens`, `supports_tools`, `deterministic_ok`, `cost_tag`.
* In `llm_query.py`: select providers by **capability**, not just name. On parse failures, auto-retry with `json_mode` model or reduce `max_tokens`.

**Where to wire:**
`aegis/utils/model_manifest_loader.py`, `aegis/utils/llm_query.py`, `aegis/schemas/runtime.py`

## 10) Test harness & goldens (med)

You’ve got regression YAMLs under `aegis/tests/regression/*.yaml` (nice!)—double down:

* Add **fake host** executors (record/replay) so CI can verify the loop without real infra.
* Build **golden traces** (JSONL) per scenario and a diff tool; fail CI if the plan/act trace regresses.
* Include **safety corpus** for prompt-injection/tool-abuse probes.

**Where to wire:**
`aegis/providers/replay_provider.py`, `aegis/tests/*`, `docs/eval/harness.md` (currently blank)

## 11) Deployment hardening (med)

You’ve got Docker/compose. Add:

* `user: 1000:1000`, `read_only: true` (except writable volumes), `cap_drop: [ALL]`, `security_opt: no-new-privileges:true`, remove `NET_RAW`, pin images by **digest**, isolate networks, and healthcheck every backend before enabling actions.

**Where to wire:**
`Dockerfile`, `docker-compose.yml`

# Docs you stubbed (fill these next)

* `docs/architecture.md`: control loop diagram, state stores, policy check path, failure modes.
* `docs/policies.md`: **matrix** of tool × role × interface × time, escalation rules, rate limits.
* `docs/observability/schema/*.json`: `tool_call.json`, `tool_result.json`, `artifact_manifest.json` to match the contracts above.
* `docs/eval/{scenarios.md,harness.md}`: how to run the fake-host harness, record goldens, and evaluate pass/fail.

# Specific receipts (what I looked at)

* Loop/graph & steps: `aegis/agents/agent_graph.py`, `aegis/agents/steps/{reflect_and_plan,execute_tool,verification,check_termination}.py`
* HITL: `aegis/agents/steps/interaction.py`, `presets/human_in_the_loop_test.yaml`
* Tooling: `aegis/registry.py`, `plugins/*.py`, `aegis/executors/*.py`
* Backends: `aegis/providers/*`, `aegis/utils/llm_query.py`
* Manifests: `machines.yaml`, `aegis/utils/machine_loader.py`, `aegis/schemas/machine.py`
* Observability: `aegis/utils/{provenance,replay_logger,artifact_manager}.py`
* Configs/presets: `config.yaml`, `presets/*.yaml`
* Tests/docs scaffolding: `aegis/tests/regression/*.yaml`, `docs/*` (many files are the blanks you created—perfect targets to fill)