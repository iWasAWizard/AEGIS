# Runbook: Operations & Recovery

This runbook contains the operational steps to diagnose and recover common faults in an AEGIS deployment.

## Quick checks

- Check service health (Docker Compose):

```bash
docker compose ps
docker compose logs aegis --tail=200
```

- Check disk space and inodes:

```bash
df -h
df -i
```

## Restarting after a crash

1. Stop: `docker compose down`
2. Prune unused images if disk is low: `docker image prune -a`
3. Start clean: `docker compose up --build -d`
4. Inspect logs: `docker compose logs --follow aegis`

## Restoring missing artifacts

If `reports/<task_id>/provenance.json` is missing but logs exist, search `logs/` for the `task_id` and reconstruct a minimal provenance file from the `ToolStart`/`ToolEnd` events.

## Escalation

- If the LLM backend (BEND) is unresponsive, check `vllm` container logs and BEND healthcheck scripts. If required, restart the BEND services and re-run `./scripts/manage.sh healthcheck`.
- For persistent storage corruption, restore from the last known good backup of `artifacts/` and `index/` directories.
