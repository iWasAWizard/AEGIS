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
from threading import RLock  # in-module sync for counters
import os
import time

_failures: dict[str, list[float]] = {}
_cooldown_until: dict[str, float] = {}
_fail_lock = RLock()
_rate_hits: dict[str, list[float]] = {}
_rate_lock = RLock()


Effect = Literal["ALLOW", "REQUIRE_APPROVAL", "DENY"]


@dataclass(frozen=True)
class PolicyDecision:
    effect: Effect
    reason: str
    policy_id: str
    when_iso: str
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
    when = when_iso or _now_iso()
    # For now, simulation simply proxies to authorize and marks the result simulated.
    dec = authorize(
        actor=actor,
        tool=tool,
        target_host=target_host,
        interface=interface,
        args=args or {},
        when_iso=when,
    )
    return PolicyDecision(
        effect=dec.effect,
        reason=dec.reason,
        policy_id=dec.policy_id,
        when_iso=when,
        simulated=True,
        metadata=dec.metadata,
    )


def record_failure(
    *, tool: str, target_host: str | None, run_id: str | None = None
) -> None:
    """Record a failure for breaker accounting and emit a trip event when threshold is crossed."""
    import os

    now = time.time()
    key = f"{tool}::{target_host or 'none'}"
    window = int(os.getenv("AEGIS_BREAKER_WINDOW_S", "120"))
    threshold = int(os.getenv("AEGIS_BREAKER_THRESHOLD", "3"))
    cooldown = int(os.getenv("AEGIS_BREAKER_COOLDOWN_S", "600"))
    with _fail_lock:
        hist = [t for t in _failures.get(key, []) if now - t <= window]
        hist.append(now)
        _failures[key] = hist

        in_cooldown = now < _cooldown_until.get(key, 0.0)
        if len(hist) >= threshold and not in_cooldown:
            _cooldown_until[key] = now + cooldown
            try:
                # Optional: structured replay event if run_id is present
                if run_id:
                    from aegis.utils.replay_logger import (
                        log_replay_event,
                    )  # lazy import to avoid cycles

                    log_replay_event(
                        run_id,
                        "BREAKER_TRIPPED",
                        {
                            "key": key,
                            "window_s": window,
                            "threshold": threshold,
                            "cooldown_s": cooldown,
                            "until": _cooldown_until[key],
                        },
                    )
            except Exception:
                pass
            try:
                # Also log a plain info line
                from aegis.utils.logger import setup_logger  # lazy

                setup_logger(__name__).info(
                    "Breaker tripped",
                    extra={
                        "event_type": "BreakerTrip",
                        "key": key,
                        "window_s": window,
                        "threshold": threshold,
                        "cooldown_s": cooldown,
                        "until": _cooldown_until[key],
                    },
                )
            except Exception:
                pass


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
    Decision surface for tools. Return ALLOW, REQUIRE_APPROVAL, or DENY.

    This bootstrap version encodes conservative defaults:
    - certain sensitive tool families REQUIRE_APPROVAL
    - host-bound tools require explicit target_host + interface
    - otherwise ALLOW
    """
    when = when_iso or _now_iso()

    # --- BEGIN STUB RULES ---
    # Require approval for certain sensitive operations by default.
    # This is intentionally coarse and can be refined later.
    if tool in ("power.shutdown", "power.reboot", "firewall.apply", "net.if.configure"):
        return PolicyDecision(
            effect="REQUIRE_APPROVAL",
            reason=f"Sensitive tool '{tool}' requires human approval",
            policy_id="bootstrap/001",
            when_iso=when,
            metadata={"target_host": target_host, "interface": interface},
        )

    # Deny obviously dangerous families unless explicitly allowed later.
    dangerous_prefixes = ("power.", "firewall.", "net.if.", "fs.mount.")
    if tool.startswith(dangerous_prefixes):
        return PolicyDecision(
            effect="REQUIRE_APPROVAL",
            reason=f"Sensitive tool '{tool}' requires human approval",
            policy_id="bootstrap/001",
            when_iso=when,
            metadata={"target_host": target_host, "interface": interface},
        )

    # Failure breaker: if cooldown active, require approval
    try:
        key = f"{tool}::{target_host or 'none'}"
        until = _cooldown_until.get(key)
        if until and time.time() < until:
            return PolicyDecision(
                effect="REQUIRE_APPROVAL",
                reason=f"breaker active until {int(until)}",
                policy_id="breaker/active",
                when_iso=when,
                metadata={"until": until, "key": key},
            )
    except Exception:
        pass

    # If no target/iface is specified for a host-bound tool, deny.
    host_bound_prefixes = ("ssh.", "scp.", "cmd.", "files.", "docker.")
    if tool.startswith(host_bound_prefixes) and not (target_host and interface):
        return PolicyDecision(
            effect="DENY",
            reason="Host-bound tool requires target_host and interface",
            policy_id="bootstrap/002",
            when_iso=when,
            metadata=None,
        )
    try:
        deny_set = {
            t.strip()
            for t in os.getenv("AEGIS_POLICY_DENY_TOOLS", "").split(",")
            if t.strip()
        }
    except Exception:
        deny_set = set()

    if tool in deny_set:
        return PolicyDecision(
            effect="DENY",
            reason=f"Tool '{tool}' is hard-denied by policy",
            policy_id="env/deny_tools",
            when_iso=when,
            metadata={"tool": tool},
        )

    # Check environment-driven require-approval list
    try:
        _max_per_min = int(os.getenv("AEGIS_POLICY_RLMAX_PER_MIN", "0"))
    except Exception:
        _max_per_min = 0

    if _max_per_min > 0:
        key = f"{tool}::{target_host or 'none'}"
        now = time.time()
        with _rate_lock:
            # Drop entries older than 60s
            hits = [t for t in _rate_hits.get(key, []) if now - t < 60.0]
            if len(hits) >= _max_per_min:
                return PolicyDecision(
                    effect="REQUIRE_APPROVAL",
                    reason=f"rate limit exceeded for {key}: {len(hits)}/{_max_per_min} in last 60s",
                    policy_id="env/rate_limit",
                    when_iso=when,
                    metadata={"window_s": 60, "count": len(hits)},
                )
            hits.append(now)
            _rate_hits[key] = hits
    try:
        require_list = {
            t.strip()
            for t in os.getenv("AEGIS_POLICY_REQUIRE_APPROVAL", "").split(",")
            if t.strip()
        }
    except Exception:
        require_list = set()

        # Host / interface allowlists: if set and not matched, require approval
    try:
        allowed_hosts = {
            h.strip()
            for h in os.getenv("AEGIS_POLICY_ALLOW_HOSTS", "").split(",")
            if h.strip()
        }
        allowed_ifaces = {
            i.strip()
            for i in os.getenv("AEGIS_POLICY_ALLOW_INTERFACES", "").split(",")
            if i.strip()
        }
    except Exception:
        allowed_hosts = set()
        allowed_ifaces = set()

    if allowed_hosts and target_host and target_host not in allowed_hosts:
        return PolicyDecision(
            effect="REQUIRE_APPROVAL",
            reason=f"target_host '{target_host}' not in allowlist",
            policy_id="env/allow_hosts",
            when_iso=when,
            metadata={"allow_hosts": sorted(allowed_hosts), "target_host": target_host},
        )

    if allowed_ifaces and interface and interface not in allowed_ifaces:
        return PolicyDecision(
            effect="REQUIRE_APPROVAL",
            reason=f"interface '{interface}' not in allowlist",
            policy_id="env/allow_ifaces",
            when_iso=when,
            metadata={"allow_ifaces": sorted(allowed_ifaces), "interface": interface},
        )

    if tool in require_list:
        return PolicyDecision(
            effect="REQUIRE_APPROVAL",
            reason=f"Tool '{tool}' requires human approval by policy",
            policy_id="env/require_approval",
            when_iso=when,
            metadata={"tool": tool, "target_host": target_host, "interface": interface},
        )

    # Default allow.
    return PolicyDecision(
        effect="ALLOW",
        reason="No matching deny/approval rules; default allow",
        policy_id="bootstrap/000",
        when_iso=when,
        metadata={"target_host": target_host, "interface": interface},
    )
    # --- END STUB RULES ---
