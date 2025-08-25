# Contract safety & preflight (Patch D)

* New CLI step `aegis preflight` (or `python -m aegis preflight`):

  * Validate `machines.yaml` strictly against `aegis/schemas/machine.py` (fields, types, ranges).
  * Validate provider profiles (backend names exist, required env present).
  * Emit a single pass/fail report with line/field pointers; non-zero exit on failure.
* Add light `model_validator`s where helpful:

  * Docker/Compose wrappers: ports in range, non-empty image, container name charset.
  * Slack/GitLab wrappers: basic ID/string sanity (non-blank, length caps).

# Security hardening (remaining nits)

* `aegis/executors/http_exec.py` (or wherever request logging happens):

  * Redact `Authorization: Bearer …`, cookies, and any `token`/`api_key` query params in logs.
* `aegis/utils/env_report.py` (we extended already) → optionally add `AWS_*`, `GCLOUD_*` prefixes if they’re ever logged as “present”.
* Policy hook (tiny) in exec path: before spawning external binaries, call a no-op authorizer (default allow). Gives you a single choke point to deny risky binaries later without touching tools.

# Uniformity: tool surface cleanup

* Retire legacy `plugins/*` at load time:

  * Ensure any auto-loader ignores `plugins/` or wrap registration in `if os.getenv("AEGIS_ENABLE_LEGACY_PLUGINS") == "1":`.
  * README note pointing to `aegis/tools/wrappers/*` names.
* Align tags/categories across wrappers (`docker`, `compose`, `slack`, `gitlab`) for UI filtering: use short nouns (`containers`, `images`, `chat`, `issues`, etc.).

# Tests that pay rent

* Unit tests:

  * Planner remediation path (`reflect_and_plan`): invalid → repaired → valid.
  * Fuzz wrappers: `allow_shell=False` vs `True`, argv substitution, timeout behavior.
  * Docker/Compose wrappers: mock executors; assert `ToolResult.meta` and spans.
* Lightweight integration:

  * Compose: bring up a tiny service, `docker.exec` a no-op, then stop. Gate behind env flag for CI.

# Tiny buglets / paper cuts I still recommend fixing

* `aegis/serve_dashboard.py` → wrap `opentelemetry.instrumentation.httpx` import in a try/except so the dashboard still runs without the extra package (log a warning).
* Anywhere tools print JSON to `stdout` as their primary output (mostly list/inspect) → ensure `ToolResult.meta={"format":"json"}` so the UI knows to pretty-render.
* Span fields: whenever a tool targets a host, include `target_host` and `interface` in span kwargs (you already do this in `execute_tool.py`; extend to wrappers that know the target).

# Optional symmetry (nice to have)

* Promote `docker.list.containers` / `docker.inspect.*` from wrapper-level SDK calls into `DockerExecutor` so **all** docker tools are executor-based (mockable the same way).
* Add `docker.list.images` (read-only) and wire it through the executor for parity.

If you want a one-liner plan of attack: **finish Patch C on the wrappers + tracing helper, ship the preflight CLI (Patch D), then the tiny security nits**. After that, tests.
