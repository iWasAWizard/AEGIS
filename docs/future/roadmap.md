# Sprint 2 — Instrument & Compare (finish line)

**Goals:** turn the tracing/telemetry foundation into actionable visibility.
**Deliverables:**

* **Langfuse MVP**: spans for plan/tool/verify + generations (tokens/cost), all best-effort and redacted.
* **A/B runner “happy path”**: `collect` + `compare` over two run dirs; results JSON and a short README.
* **Provider coverage**: extend `log_generation(...)` to any other active providers (as applicable).
* **Dash stubs**: one simple chart per run set (success%, avg steps/run, breaker trips/run).
  **Exit criteria:** traces visible for multiple runs; A/B compare prints deltas; dashboards render basic metrics.

# Sprint 3 — Goal Graph (DAG) Pilot

**Goals:** enable parallelizable goals with safe gating.
**Deliverables:**

* **Data model**: `GoalNode{id,text,requires,status}` + `state.goal_graph`.
* **Ready-set**: compute nodes with all prereqs `done`; planner only chooses from ready set.
* **PromptBuilder nudge**: list “Ready nodes:” when a graph exists (fallback to linear mode otherwise).
* **Provenance**: `NODE_START / NODE_DONE / NODE_BLOCKED` events.
* **(Optional)** advisory guardrails hook in `policy.authorize(...)` (single call-site; advisory only).
  **Exit criteria:** diamond graph (A→B, A→C, B\&C→D) runs with B/C in any order; D unlocks only when ready; unrelated branches keep moving if one is blocked/needs approval.

# Sprint 4 — Model Capability Flags & Fallbacks

**Goals:** pick the right model reliably and downgrade safely.
**Deliverables:**

* **`models.yaml` flags**: `ctx_window`, `json_mode`, `function_calling`, `cost_tier`.
* **Selector**: never choose non-JSON for JSON prompts; detect projected overflow and **fallback** to a compatible model with a log note.
* **Tests**: unit tests for selector; golden run showing fallback behavior.
  **Exit criteria:** selector logs choice + reason; JSON prompts never hit non-JSON models; overflow triggers a deterministic fallback.

# Sprint 5 — Distributed Breakers & Deployment Polish

**Goals:** make breakers multi-worker safe and tighten ops.
**Deliverables:**

* **Redis breaker state**: move `_failures/_cooldown_until` to Redis (atomic increments, TTL’d keys per `tool::host`).
* **Telemetry**: `BREAKER_TRIPPED` emitted once at threshold; cooldown expiry logged.
* **Compose healthchecks**: liveness/readiness for API/worker/model backends.
* **Model lister**: `scripts/list-models.sh` or Python equivalent that prints available models per provider.
* **(Optional)** `/transcribe` & `/speak` proxies if those endpoints are part of your stack.
  **Exit criteria:** breaker trips correctly with two workers running concurrently; healthchecks turn containers healthy; model-lister prints a sensible inventory.

---

## Dependencies

* Sprint 2 precedes the A/B-focused comparisons in later sprints (you’ll use those metrics to judge DAG & selector quality).
* Capability flags must land before selection/fallback logic.
* Redis breaker depends on a Redis URL being available in the environment.

## Ready-to-mint ticket titles (one-liners)

* `dag: add GoalNode model + ready-set computation`
* `dag: PromptBuilder "Ready nodes" + planner choice`
* `dag: provenance events NODE_START/DONE/BLOCKED`
* `models: add capability flags to models.yaml`
* `models: implement selector + overflow fallback`
* `policy: breaker → Redis (atomic, TTL)`
* `deploy: compose healthchecks + model-lister`
* `obs: Langfuse MVP (spans + generations)`
* `eval: A/B runner README + example`

When you’re back, we can start with DAG’s tiny data model and ready-set function (about a dozen lines) or jump straight to capability flags—your call.
