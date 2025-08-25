# AEGIS API Reference

The AEGIS API provides a set of RESTful endpoints for launching and managing autonomous agent tasks. It is served by a FastAPI application and uses Pydantic for strict data validation and serialization.

Base URL: `http://localhost:8000/api`

---

## Primary endpoint

### POST /launch

Initiate a new agent task. Accepts a `LaunchRequest` JSON payload. The endpoint is blocking: it will return when the agent completes or pauses waiting for human input.

Request JSON (high-level)

- `task` (object, required)
  - `prompt` (string, required)
  - `task_id` (string, optional)
- `config` (string|object, required)
  - If a string, this must be a preset ID (for example, `verified_flow`).
  - If an object, it must conform to `AgentConfig`.
- `execution` (object, optional)
  - `backend_profile` (string)
  - `llm_model_name` (string)
  - `iterations` (integer)
  - `safe_mode` (boolean)
  - `tool_allowlist` (array[string])

Example request (JSON):

```json
{
  "task": { "prompt": "Create a file named 'report.txt' and write the current date into it." },
  "config": "verified_flow",
  "execution": { "backend_profile": "vllm_local", "iterations": 10 }
}
```json

Responses

- 200 OK — `LaunchResponse` object
  - `task_id` (string)
  - `summary` (string, markdown)
  - `status` (string: `COMPLETED` | `PAUSED` | `FAILURE`)
  - `history` (array of step objects: `thought`, `tool_name`, `tool_args`, `tool_output`)
- 400 Bad Request — payload validation error
- 500 Internal Server Error — runtime error (e.g., PlannerError, ToolExecutionError)

Quick example (curl, blocking launch):

```bash
curl -s -X POST http://localhost:8000/api/launch \
  -H "Content-Type: application/json" \
  -d '{"task": {"prompt": "Write the current date to /tmp/date.txt"}, "config": "verified_flow", "execution": {"backend_profile": "vllm_local", "iterations": 5}}'
```bash

---

## Human-in-the-loop endpoint

### POST /resume

Resume a paused task (agent requested human input via `ask_human_for_input`).

Request body

- `task_id` (string, required)
- `human_feedback` (string, required)

Example:

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "human_feedback": "Yes, you have my permission to proceed."
}
```json

Responses

- 200 OK — resumed and completed; returns `LaunchResponse`
- 404 Not Found — `task_id` not paused or unknown

---

## Informational endpoints

These `GET` endpoints are used by the UI.

- GET `/inventory` — list tools and their input schemas
- GET `/presets` — list agent presets
- GET `/backends` — list backend profiles
- GET `/models?backend_profile=<name>` — models for a backend
- GET `/artifacts` — list artifact entries
- GET `/artifacts/{task_id}/summary` — human-readable markdown summary
- GET `/artifacts/{task_id}/provenance` — raw provenance JSON

---

## WebSocket

### GET /ws/logs

WebSocket for real-time logs. Protocol: `ws` or `wss`. The server pushes JSON or plain text log messages. The connection is server-to-client.
