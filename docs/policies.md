# Runtime Policies and Guardrails

AEGIS supports configurable runtime policies to control what agents are allowed to do, which tools are permitted, and when human approval is required. Policies are enforced at runtime by the `policy` layer and can be configured globally (in `config.yaml`) or per-task via the `execution` override block.

## Policy types

- Allowlist/denylist: Limit the set of tools an agent can invoke. Use `tool_allowlist` or `tool_denylist` in task overrides.
- Human-in-the-loop (HITL): Mark nodes in a preset with `interrupt_nodes` so the agent pauses for human confirmation.
- Resource policies: Restrict access to machines, file paths, or external network hosts.
- Safety checks: Block operations deemed unsafe by configured guardrails (e.g., remote code execution on production hosts).

## Example (task-level policy overrides)

```yaml
execution:
  tool_allowlist:
    - read_file
    - list_dir
  safe_mode: true
  human_intervention_required: true
```

## Enforcement behavior

- Policy checks run before tool invocation. If a requested tool is not allowed, the planner receives a `ToolNotAllowedError` and will re-plan.
- If a tool is allowed but the resource is disallowed (for example, path `/etc/` when restricted), the tool raises `ToolExecutionError` and the event is marked `failure`.
- For HITL, tasks move to `PAUSED` and the UI exposes a resume endpoint (`/api/resume`) to continue the run with human feedback.

## Best practices

- Prefer `tool_allowlist` for high-security environments rather than denylists.
- Use `interrupt_nodes` sparingly in automated CI runs; prefer human checkpoints in staging.
- Log all policy denials with `level=warning` and include the `task_id` and offending `tool_name` in the structured log.

## Notes

- The policies system is intentionally pluggable. If you need a custom authorization flow (LDAP, OAuth), implement the hook in `aegis/utils/policy.py`.
