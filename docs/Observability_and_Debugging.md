# Operational Guide: Observability & Debugging

An autonomous agent can feel like a "black box." When it works, it's magic. When it fails, it can be frustrating to figure out why. The AEGIS framework is built to be highly observable, giving you the tools you need to open that black box and understand exactly what's happening.

This guide will walk you through a typical debugging workflow for an agent task using the tools built directly into AEGIS.

## The Two Key Views: The UI and The Provenance Report

Effective debugging in AEGIS involves using two different views together:

1.  **The AEGIS UI (`http://localhost:8000`):** This is your **control panel and real-time monitor**. It's where you launch tasks and, most importantly, watch the live, structured logs stream in from the agent as it works.
2.  **The Provenance Report (`reports/<task_id>/provenance.json`):** This is your **microscope and flight data recorder**. After a task is complete, this machine-readable JSON file gives you a perfect, step-by-step record of the agent's *entire* thought process.

## Scenario: Debugging a Failed Task

Let's imagine you give the agent the following prompt:

> "Read the contents of the file at '/etc/non_existent_file.txt' on the 'ubuntu-qemu' machine and tell me what it says."

This task is designed to fail, because the file doesn't exist. Let's see how we would debug this.

### Step 1: Launch the Task in AEGIS

1.  Navigate to the **Launch** tab in the AEGIS UI.
2.  Select the `Verified Agent Flow` preset.
3.  Select the `vllm_local` backend profile.
4.  Enter the prompt above.
5.  Click **"Launch Task"**.

As the agent runs, you will see structured JSON logs appear in the **Live Task Logs** panel. These logs provide real-time insight. You might see an `INFO` log for the `ToolStart` event, followed quickly by an `ERROR` log for the `ToolEnd` event, giving you your first clue that something went wrong during execution.

### Step 2: Open the Artifacts in the UI

Once the task completes, navigate to the **Artifacts** tab.

1.  You will see a new entry at the top of the list for your recent task. The status will likely be `FAILURE` or `PARTIAL`.
2.  Click on the entry to expand it.

### Step 3: Analyze the Provenance Report

Click on the **Provenance** tab within the expanded artifact view. This shows you the detailed JSON report of the task. This is the heart of the debugging process.

Here's how to read it:

1.  **`task_prompt`:** The top-level key confirms the exact goal you gave the agent.
2.  **`events`:** This is an array containing the step-by-step history. Find the event that failed.
    -   **`thought`:** You can see the agent's reasoning *before* it acted. Did it correctly decide to use `read_remote_file`?
    -   **`tool_name` and `tool_args`:** You can verify the exact tool and arguments it used (e.g., `{"machine_name": "ubuntu-qemu", "file_path": "/etc/non_existent_file.txt"}`).
    -   **`observation`:** This is the most important field for debugging. Here, you will see the full error message returned by the tool, something like `[ERROR] ToolExecutionError: Remote command failed with exit code 1. Output: [STDERR]\ncat: /etc/non_existent_file.txt: No such file or directory`.
    -   **`status`:** This will be marked as `failure`.

### Step 4: Form a Hypothesis

From the provenance report, we have a complete picture:

-   We can see from the `thought` that the agent correctly understood the goal.
-   We can see that it correctly chose the `read_remote_file` tool.
-   We can see that the tool failed with a "No such file or directory" error.

Our hypothesis is simple: **The agent's plan was correct, but the state of the world (the file's non-existence) caused a tool failure.**

If the agent had made a different mistake (e.g., hallucinating a tool name like `read_a_file`), we would have seen a `ToolNotFoundError` in the `observation`. If it had produced bad JSON for its plan, we would see a `PlannerError` and the task would have likely failed before any tools were even run.

By using the live logs for real-time monitoring and the detailed provenance report for post-mortem analysis, you can move from guessing what the agent did to knowing *exactly* what it did, why it did it, and where it went wrong.

## Provenance schema (technical)

AEGIS produces a machine-readable provenance report for every completed task. The report lives under the `reports/<task_id>/` directory alongside other artifacts. A canonical `provenance.json` contains the full execution trace and is intended to be both human- and machine- consumable.

Common top-level keys you'll see in `provenance.json`:

- `task_id` (string): UUID for the run.
- `task_prompt` (string): The original natural-language goal supplied at launch.
- `status` (string): Final status, e.g. `COMPLETED`, `PARTIAL`, `FAILURE`, `PAUSED`.
- `started_at` / `finished_at` (ISO 8601 timestamps): Run boundaries.
- `events` (array): Ordered list of step events. Each event is an object with fields described below.

Each event in `events` contains (typical fields):

- `timestamp` (ISO 8601) — when the event was emitted.
- `step_id` (string) — logical name of the step (for example `plan`, `execute`, `observe`).
- `kind` (string) — high-level category, e.g. `thought`, `tool_call`, `tool_result`, `observation`.
- `thought` (string, optional) — the agent's reasoning text for planning steps.
- `tool_name` (string, optional) — the tool invoked, e.g. `read_remote_file`.
- `tool_args` (object, optional) — the exact arguments passed to the tool.
- `tool_call` (object, optional) — the serialized call metadata: start/end timestamps, exit code (if applicable), streaming flags.
- `tool_result` (object, optional) — canonical result returned by the tool. For complex tools this will include nested fields for stdout/stderr, file paths, or JSON payloads.
- `observation` (string/object, optional) — the textual or structured observation recorded after running a tool; includes error stacktraces for failures.
- `status` (string) — event outcome such as `success`, `failure`, `skipped`.

Because the provenance format is intentionally structured, you can write small tools to:

- Reconstruct the full sequence of thoughts and actions for auditability.
- Extract all tool invocations that touched a particular machine, file, or external service.
- Re-run or replay tool calls in an isolated test harness.

## Live logs and structured logging

AEGIS writes two complementary kinds of logging:

- Real-time, human-friendly logs streamed to the UI and optionally to stdout/stderr.
- Structured `.jsonl` logs (one JSON object per line) stored in the `logs/` directory. These are suitable for ingestion into ELK, Loki, or any JSON-aware log store.

Log fields you will commonly see in `.jsonl` files:

- `time` (ISO 8601)
- `level` (`DEBUG`/`INFO`/`WARNING`/`ERROR`)
- `task_id` (optional)
- `event_kind` (`ToolStart`, `ToolEnd`, `AgentThought`, `Error`)
- `payload` (object) — tool args, return codes, truncated stdout/stderr, and redacted secrets when applicable.

AEGIS redacts secrets automatically from logs using configured redaction rules; sensitive fields (passwords, API keys) are replaced or omitted.

## Where artifacts are stored

- `reports/<task_id>/provenance.json` — canonical provenance report.
- `reports/<task_id>/summary.md` — human-readable markdown summary produced by the summarizer step.
- `artifacts/<task_id>/` — arbitrary files created by tools (screenshots, downloaded files, job logs).
- `logs/` — global `.jsonl` log files for ingestion and debugging.

## Debugging checklist (practical)

1. Reproduce the run (if possible) using the same preset/config. Use the `task_id` from the UI or API.
2. Open `reports/<task_id>/provenance.json` and find the first `status: failure` event in `events`.
3. Inspect the `tool_args` and `tool_result` fields for that event. If the tool returned non-zero exit code, `tool_result` will usually include `exit_code`, `stdout`, and `stderr`.
4. Use the UI's **Live Task Logs** to see the streaming sequence that led to the failure — timestamps here can be helpful to correlate with external services.
5. If the failure is external (network, backend), check the service health (`docker compose ps`, `./scripts/manage.sh healthcheck` for BEND) and the provider logs.
6. If the failure is a logic/hallucination bug (planner picked the wrong tool or malformed args), inspect the preceding `thought` event to see what the agent was thinking.

## Example: common failure modes

- Missing resource (file/host) — tool returns `stderr` showing `No such file or directory` and event `status: failure`.
- Unauthorized — tools that contact remote services will surface `401`/`403` in `tool_result` or `observation` and often `"unauthorized"` in the error message.
- Timeout — tools that rely on network calls will show `timeout` in `tool_result` and may have partial `stdout` present.

## Access provenance via API

You can retrieve the provenance JSON for a task with the artifacts API endpoint:

GET /api/artifacts/{task_id}/provenance

This returns the raw `provenance.json` file. The UI uses the same endpoint to populate the Provenance tab.

## Small automation ideas


## Notes and troubleshooting



If you want, I can now create a small reference extractor script that loads a `provenance.json` and prints a compact failure summary (tool, args, stderr) for CI/alerting — tell me if you want that and where to place it in the repo.
If you want, I created a small reference extractor script at `scripts/extract_provenance_failure.py` that loads a `provenance.json` and prints a compact failure summary (tool, args, stderr) useful for CI/alerts and quick troubleshooting.

## Canonical provenance fields (reference table)

Top-level keys in `reports/<task_id>/provenance.json` (concise reference):

| Key | Type | Meaning |
|---|---:|---|
| `task_id` | string | UUID for the run |
| `task_prompt` | string | Original natural-language goal |
| `status` | string | Final status: `COMPLETED` / `PARTIAL` / `FAILURE` / `PAUSED` |
| `started_at`, `finished_at` | ISO8601 | Run timestamps |
| `events` | array | Ordered list of step events (see event table below) |

Event object fields (common):

| Field | Type | Notes |
|---|---:|---|
| `timestamp` | ISO8601 | When the event was emitted |
| `step_id` | string | Logical step name (e.g. `plan`, `execute`) |
| `kind` | string | `thought` / `tool_call` / `tool_result` / `observation` |
| `thought` | string | Planner reasoning text (present for planning steps) |
| `tool_name` | string | Tool invoked (e.g. `read_remote_file`) |
| `tool_args` | object | Exact args passed to the tool (machine/file/etc.) |
| `tool_call` | object | Call metadata: start/end, exit codes, streaming flags |
| `tool_result` | object | Tool output shape: stdout/stderr/paths/structured payloads |
| `observation` | string/object | Final observation or error message |
| `status` | string | `success` / `failure` / `skipped` |

## Quick CLI recipes (practical)

Extract the first failure event from a local provenance file using `jq`:

```bash
# print the first failure event as compact JSON
jq -c '.events[] | select(.status=="failure") | {timestamp, step_id, tool_name, tool_args, observation} | . ' reports/<task_id>/provenance.json | head -n1
```

List all runs that invoked a particular tool (search across reports):

grep -R "\"tool_name\": \"read_remote_file\"" -n reports/ || true
```bash
grep -R "\"tool_name\": \"read_remote_file\"" -n reports/ || true
```

Fetch provenance via the API and show the failing observation (requires jq + curl):

```bash
curl -s http://localhost:8000/api/artifacts/<task_id>/provenance | jq '.events[] | select(.status=="failure") | {timestamp, tool_name, observation}' | head -n1
```

## ASCII diagnostic diagrams

Minimal timeline for a failing file-read task:

```text
Client -> API: POST /api/launch { prompt }
API -> AgentGraph: compile & start
AgentGraph: plan -> thought (chooses read_remote_file)
AgentGraph -> Executor: run read_remote_file(args)
Executor -> RemoteHost: cat /etc/non_existent_file.txt
RemoteHost -> Executor: EXIT 1, stderr: "No such file"
Executor -> AgentGraph: tool_result(status=failure, stderr)
AgentGraph -> API: LaunchResponse(status=FAILURE)
```

Tools and observability flow (compact):

```text
logs/ (jsonl)  --> centralized log store (ELK/Loki)
reports/       --> provenance.json + summary.md
artifacts/     --> binary artifacts and files
```

## Suggested automated checks (CI)

- Small golden-run smoke tests that assert `status == COMPLETED` for simple end-to-end presets.
- A nightly index job that counts `events[] | select(.status=="failure")` per tool and alerts on regression spikes.

## Helper script

I added a tiny helper script at `scripts/extract_provenance_failure.py` which prints a one-line summary for the first failure found in a given provenance file (tool, args, and stderr). Use it like:

```bash
# local file
python3 scripts/extract_provenance_failure.py reports/<task_id>/provenance.json

# or via API (save to tmp then run):
curl -s http://localhost:8000/api/artifacts/<task_id>/provenance -o /tmp/p.json && python3 scripts/extract_provenance_failure.py /tmp/p.json
```

---

If you'd like, I can (next) add an automation that indexes `events` into Elasticsearch or generate a small Grafana dashboard ASCII mock that you can export to JSON for import.
