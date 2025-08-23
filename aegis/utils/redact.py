# aegis/utils/redact.py
"""
Lightweight log redaction helpers.

Goal: prevent sensitive material (tokens, passwords, secrets) from appearing in logs,
while preserving structure and non-sensitive fields for debuggability.

Usage:
    from aegis.utils.redact import redact_for_log

    safe_args = redact_for_log(plan.tool_args)
    logger.info("Executing tool", extra={"tool_args": safe_args})

Notes:
- This is **for logs only**. Do NOT use it to mutate/strip data used by the agent.
- Redaction is best-effort and opinionated; expand PATTERNS as needed.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Sequence

# Case-insensitive key substrings that imply sensitive values
KEY_PATTERNS = [
    "password",
    "passwd",
    "secret",
    "token",
    "apikey",
    "api_key",
    "auth",
    "authorization",
    "cookie",
    "session",
    "private_key",
    "ssh_key",
    "jwt",
    "bearer",
    "credential",
    "client_secret",
    "access_key",
    "refresh_token",
]

# Regexes that suggest a value *content* is sensitive (e.g., looks like a bearer/jwt)
VALUE_PATTERNS = [
    re.compile(r"^Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*$", re.IGNORECASE),
    re.compile(
        r"^eyJ[a-zA-Z0-9_\-]+?\.[a-zA-Z0-9_\-]+?\.[a-zA-Z0-9_\-]+$"
    ),  # naive JWT
    re.compile(r"^[A-Za-z0-9_\-]{24,}$"),  # long opaque tokens/ids
]


REDACTED = "********"


def _looks_sensitive_key(key: str) -> bool:
    k = key.lower()
    return any(p in k for p in KEY_PATTERNS)


def _looks_sensitive_value(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    s = val.strip()
    if not s:
        return False
    return any(rx.search(s) for rx in VALUE_PATTERNS)


def _redact_primitive(val: Any) -> Any:
    if isinstance(val, str):
        # Keep length hint (to preserve structure in logs)
        if len(val) <= 8:
            return REDACTED
        return f"{REDACTED}({len(val)})"
    # Non-strings -> generic star hint
    return REDACTED


def redact_for_log(obj: Any) -> Any:
    """
    Return a structurally similar object with sensitive material masked.

    - Dict: redact by key heuristics; recurse values.
    - Sequence: recurse each element.
    - String: redact if it matches sensitive value patterns; else pass through.
    - Everything else: pass through.
    """
    try:
        if isinstance(obj, Mapping):
            out: Dict[str, Any] = {}
            for k, v in obj.items():
                if _looks_sensitive_key(str(k)) or _looks_sensitive_value(v):
                    out[k] = _redact_primitive(v)
                else:
                    out[k] = redact_for_log(v)
            return out
        elif isinstance(obj, (list, tuple)):
            t = type(obj)
            return t(redact_for_log(x) for x in obj)
        elif isinstance(obj, str):
            return _redact_primitive(obj) if _looks_sensitive_value(obj) else obj
        else:
            return obj
    except Exception:
        # Fail-open, best effort: return a generic token if anything goes sideways
        return REDACTED
