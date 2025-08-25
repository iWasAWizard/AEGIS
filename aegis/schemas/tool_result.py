# aegis/schemas/tool_result.py
"""
Standard ToolResult with provenance, truncation flags, and artifact refs.

Backwards compatible fields kept:
- success, stdout, stderr, exit_code, error_type, latency_ms, target_host, interface, meta

New fields:
- tool_name, run_id, machine_id
- args_schema_hash, redaction_hash
- truncated: {"stdout": bool, "stderr": bool}
- artifact_refs: list of ArtifactRef (path, size, sha256, mime, name)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class ArtifactRefModel(BaseModel):
    path: str
    size_bytes: int
    sha256: str
    mime: Optional[str] = None
    name: Optional[str] = None


class ToolResult(BaseModel):

    @model_validator(mode="after")
    def _auto_tag_json_meta(self) -> "ToolResult":
        """
        Auto-tag JSON-ish stdout for UI pretty rendering.
        Non-invasive: only sets meta["format"] when stdout starts with '{' or '['
        and meta.format isn't already set.
        """
        try:
            s = (self.stdout or "").lstrip()
            if s and s[0] in "{[":
                meta = dict(self.meta or {})
                if meta.get("format") != "json":
                    meta["format"] = "json"
                    self.meta = meta
        except Exception:
            # Never fail object creation due to tagging
            pass
        return self

    # Basic outcome
    success: bool = Field(..., description="True on success, False on error")
    stdout: Optional[str] = Field(
        None, description="Primary textual output (truncated by guardrails)"
    )
    stderr: Optional[str] = Field(
        None, description="Error textual output (truncated by guardrails)"
    )
    exit_code: Optional[int] = Field(
        None, description="Process-style exit code, 0 on success when applicable"
    )
    error_type: Optional[str] = Field(
        None,
        description="Short error category (Timeout|Auth|NotFound|Runtime|Parse|...)",
    )
    latency_ms: int = Field(0, description="Milliseconds spent in the tool")
    meta: Optional[Dict[str, Any]] = Field(
        default=None, description="Supplemental metadata"
    )

    # Target context (optional)
    target_host: Optional[str] = Field(
        None, description="Target host (SSH, HTTP, etc.)"
    )
    interface: Optional[str] = Field(
        None, description="Logical interface name (e.g., mgmt0)"
    )
    machine_id: Optional[str] = Field(
        None, description="Machine manifest id when available"
    )

    # Provenance
    tool_name: Optional[str] = Field(
        None, description="Registry tool key (e.g., ssh.exec)"
    )
    run_id: Optional[str] = Field(None, description="High-level run/session ID")
    args_schema_hash: Optional[str] = Field(
        None, description="SHA256 of input model JSON schema"
    )
    redaction_hash: Optional[str] = Field(
        None, description="SHA256 of redacted-args preview"
    )

    # Guardrails & artifacts
    truncated: Optional[Dict[str, bool]] = Field(
        default=None, description="Which top-level fields were truncated"
    )
    artifact_refs: Optional[List[ArtifactRefModel]] = Field(
        default=None, description="Externalized payloads"
    )

    # ----- Builders (backward-compatible) -----

    @classmethod
    def ok_result(
        cls,
        *,
        stdout: Optional[str] = None,
        exit_code: Optional[int] = None,
        latency_ms: int = 0,
        target_host: Optional[str] = None,
        interface: Optional[str] = None,
        machine_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "ToolResult":
        return cls(
            success=True,
            stdout=stdout,
            stderr=None,
            exit_code=exit_code,
            error_type=None,
            latency_ms=latency_ms,
            target_host=target_host,
            interface=interface,
            machine_id=machine_id,
            meta=meta or None,
        )

    @classmethod
    def err_result(
        cls,
        *,
        error_type: str,
        stderr: Optional[str] = None,
        latency_ms: int = 0,
        target_host: Optional[str] = None,
        interface: Optional[str] = None,
        machine_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "ToolResult":
        return cls(
            success=False,
            stdout=None,
            stderr=stderr,
            exit_code=None,
            error_type=error_type,
            latency_ms=latency_ms,
            target_host=target_host,
            interface=interface,
            machine_id=machine_id,
            meta=meta or None,
        )

    # ----- Compatibility & convenience -----

    @property
    def ok(self) -> bool:
        # Back-compat alias for older tests/usages
        return bool(self.success)

    def enforce_truncation(self, max_stdio_bytes: int) -> None:
        """
        Backward-compatible helper: truncate stdout/stderr in-place if they exceed `max_stdio_bytes`.
        Unlike `attach_artifacts_and_truncate`, this does NOT write artifacts; it only trims.
        """
        if not isinstance(max_stdio_bytes, int) or max_stdio_bytes <= 0:
            return

        trunc: Dict[str, bool] = dict(self.truncated or {})

        def _trim(field: str, value: Optional[str]) -> Optional[str]:
            if value is None:
                return None
            b = value.encode("utf-8", errors="replace")
            if len(b) <= max_stdio_bytes:
                trunc[field] = False
                return value
            head = b[:max_stdio_bytes]
            trunc[field] = True
            return head.decode("utf-8", errors="replace")

        self.stdout = _trim("stdout", self.stdout)
        self.stderr = _trim("stderr", self.stderr)
        if trunc:
            self.truncated = trunc

    # ----- Enrichment & guardrails helpers -----

    def enrich_provenance(
        self,
        *,
        tool_name: Optional[str],
        run_id: Optional[str],
        args_schema_hash: Optional[str],
        redaction_hash: Optional[str],
        machine_id: Optional[str] = None,
    ) -> None:
        self.tool_name = tool_name or self.tool_name
        self.run_id = run_id or self.run_id
        self.args_schema_hash = args_schema_hash or self.args_schema_hash
        self.redaction_hash = redaction_hash or self.redaction_hash
        if machine_id and not self.machine_id:
            self.machine_id = machine_id

    def attach_artifacts_and_truncate(
        self,
        *,
        tool_name: str,
        run_id: Optional[str],
        max_stdio_bytes: int,
        store_fn,  # callable(name:str, data:bytes)->ArtifactRef or None
    ) -> None:
        """
        Truncates stdout/stderr if they exceed max_stdio_bytes and writes full content as artifacts.
        """
        truncated_flags: Dict[str, bool] = {}
        refs: List[ArtifactRefModel] = []

        def _handle(field_name: str, text: Optional[str]) -> Optional[str]:
            if text is None:
                return None
            b = text.encode("utf-8", errors="replace")
            if len(b) <= max_stdio_bytes:
                truncated_flags[field_name] = False
                return text
            # Store full content
            ref = store_fn(preferred_name=f"{field_name}.txt", data=b)
            if ref is not None:
                refs.append(ArtifactRefModel(**ref.__dict__))
            # Truncate visible payload
            head = b[:max_stdio_bytes]
            truncated_flags[field_name] = True
            return head.decode("utf-8", errors="replace")

        self.stdout = _handle("stdout", self.stdout)
        self.stderr = _handle("stderr", self.stderr)

        if truncated_flags:
            self.truncated = truncated_flags
        if refs:
            self.artifact_refs = (self.artifact_refs or []) + refs
