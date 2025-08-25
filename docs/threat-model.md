# Threat Model

This document summarizes the primary attack surfaces and recommended mitigations for running AEGIS in production.

## Primary Attack Surfaces

1. Network-exposed APIs (FastAPI endpoints, admin UI)
2. LLM backends and third-party provider credentials
3. Tool executors that perform filesystem, network, or command execution
4. Machine manifests containing credentials and reachable hosts
5. Artifacts and logs that may contain sensitive data

## Threats and Mitigations

- Unauthorized API access
	- Mitigation: Front AEGIS with an auth proxy (OIDC/OAuth2). Require `Authorization` header for all write endpoints.

- Credential leakage in logs or artifacts
	- Mitigation: Use built-in redaction rules, store secrets in environment variables (not in YAML), and audit `logs/` and `reports/` regularly.

- Malicious or malformed tool inputs causing command injection
	- Mitigation: Strict Pydantic validation on tool inputs, input sanitization in shell wrapper, and safe-mode defaults that deny destructive tools.

- Compromise of execution hosts (machines.yaml entries)
	- Mitigation: Use network segmentation, limit tooling to non-production hosts, and rotate credentials frequently.

- LLM prompt injection or hallucination leading to unsafe plans
	- Mitigation: Use policy layer (`policies.md`), require `human_intervention` for sensitive actions, and instrument planning with guardrails.

## Operational Recommendations

- Maintain a read-only copy of `machines.yaml` for production and a separate test manifest for dev.
- Enable audit logging and export logs to an external system (Loki/ELK) with retention rules.
- Regularly scan the repository for accidentally committed secrets (use `git-secrets` or similar pre-commit hooks).
