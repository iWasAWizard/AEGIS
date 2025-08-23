# aegis/utils/policy.py
"""
Thin policy interface for action authorization.

This file intentionally does NOT implement business logic; it provides a stable
surface the rest of the system can call. Plug your real rules in later without
changing callers.

Typical call sites:
    decision = authorize(actor="agent", tool="ssh.exec",
                         target_host="10.0.0.12", interface="mgmt0",
                         args={"cmd":"systemctl restart foo"})
    if decision["effect"] == "DENY": ...
    elif decision["effect"] == "REQUIRE_APPROVAL": ...
"""

from __future__ import annotations

from typing import Literal, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


Effect = Literal["ALLOW", "REQUIRE_APPROVAL", "DENY"]


@dataclass(frozen=True)
class PolicyDecision:
    effect: Effect
    reason: str
    policy_id: str = "default"
    simulated: bool = False
    metadata: Dict[str, Any] | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def simulate(
    *,
    actor: str,
    tool: str,
    target_host: Optional[str] = None,
    interface: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
    when_iso: Optional[str] = None,
) -> PolicyDecision:
    """
    Non-binding preview of what authorize() would return for the given action.
    Use this in planning to avoid proposing actions that would be denied.
    """
    dec = authorize(
        actor=actor,
        tool=tool,
        target_host=target_host,
        interface=interface,
        args=args,
        when_iso=when_iso,
    )
    # mark as simulated
    return PolicyDecision(
        effect=dec.effect,
        reason=dec.reason,
        policy_id=dec.policy_id,
        simulated=True,
        metadata=dec.metadata,
    )


def authorize(
    *,
    actor: str,
    tool: str,
    target_host: Optional[str] = None,
    interface: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
    when_iso: Optional[str] = None,
) -> PolicyDecision:
    """
    Authoritative decision for the given action. Replace the stub logic below
    with your real rule evaluation (e.g., OPA/Rego, YAML matrix, or Python rules).
    """
    when = when_iso or _now_iso()

    # --- BEGIN STUB RULES (safe defaults) ---
    # Deny obviously dangerous families unless explicitly allowed later.
    dangerous_prefixes = ("power.", "firewall.", "net.if.", "fs.mount.")
    if tool.startswith(dangerous_prefixes):
        return PolicyDecision(
            effect="REQUIRE_APPROVAL",
            reason=f"Sensitive tool '{tool}' requires human approval",
            policy_id="bootstrap/001",
            metadata={"when": when, "target_host": target_host, "interface": interface},
        )

    # If no target/iface is specified for a host-bound tool, deny.
    host_bound_prefixes = ("ssh.", "scp.", "cmd.", "files.", "docker.")
    if tool.startswith(host_bound_prefixes) and not (target_host and interface):
        return PolicyDecision(
            effect="DENY",
            reason="Host-bound tool requires target_host and interface",
            policy_id="bootstrap/002",
            metadata={"when": when},
        )

    # Default allow.
    return PolicyDecision(
        effect="ALLOW",
        reason="No matching deny/approval rules; default allow",
        policy_id="bootstrap/000",
        metadata={"when": when, "target_host": target_host, "interface": interface},
    )
    # --- END STUB RULES ---
