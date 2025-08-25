# aegis/tools/wrappers/compose.py
from __future__ import annotations

from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field

from aegis.registry import tool
from aegis.schemas.tool_result import ToolResult
from aegis.executors.compose_exec import ComposeExecutor
from aegis.utils.tracing import span  # observability


# ---------- Input models ----------


class ComposeUpInput(BaseModel):
    project_dir: Optional[str] = Field(default=None, description="Working directory")
    file: Optional[str] = Field(default=None, description="Compose file path")
    profiles: Optional[List[str]] = None
    services: Optional[List[str]] = None
    build: bool = False
    detach: bool = True
    remove_orphans: bool = False
    pull: Optional[Literal["always", "missing", "never"]] = None
    project_name: Optional[str] = None
    scales: Optional[Dict[str, int]] = None
    timeout: Optional[int] = None


class ComposeDownInput(BaseModel):
    project_dir: Optional[str] = None
    file: Optional[str] = None
    volumes: bool = False
    remove_orphans: bool = False
    project_name: Optional[str] = None
    timeout: Optional[int] = None


class ComposePsInput(BaseModel):
    project_dir: Optional[str] = None
    file: Optional[str] = None
    project_name: Optional[str] = None
    timeout: Optional[int] = None


class ComposeLogsInput(BaseModel):
    project_dir: Optional[str] = None
    services: Optional[List[str]] = None
    file: Optional[str] = None
    project_name: Optional[str] = None
    tail: Optional[int] = None
    timestamps: bool = False
    follow: bool = False
    timeout: Optional[int] = None


# ---------- Helpers ----------


def _ensure_json_meta(res: ToolResult) -> ToolResult:
    try:
        s = (res.stdout or "").lstrip()
        if s and s[0] in "{[":
            meta = dict(res.meta or {})
            if meta.get("format") != "json":
                meta["format"] = "json"
                res.meta = meta
    except Exception:
        pass
    return res


# ---------- Tool shims (return ToolResult) ----------


@tool("compose.up", ComposeUpInput, timeout=600)
def compose_up(*, input_data: ComposeUpInput) -> ToolResult:
    """
    Bring up services via Docker Compose (build/pull/scale supported).
    Returns stdout text (JSON if your compose version supports it for some subcommands).
    """
    with span(
        "wrapper.compose.up",
        project_dir=input_data.project_dir,
        file=bool(input_data.file),
        services=len(input_data.services or []),
        detach=input_data.detach,
        build=input_data.build,
        remove_orphans=input_data.remove_orphans,
        pull=input_data.pull,
        project_name=input_data.project_name,
        scales=bool(input_data.scales),
    ):
        ex = ComposeExecutor(project_dir=input_data.project_dir)
        return ex.up_result(
            project_dir=input_data.project_dir,
            file=input_data.file,
            profiles=input_data.profiles,
            services=input_data.services,
            build=input_data.build,
            detach=input_data.detach,
            remove_orphans=input_data.remove_orphans,
            pull=input_data.pull,
            project_name=input_data.project_name,
            scales=input_data.scales,
            timeout=input_data.timeout,
        )


@tool("compose.down", ComposeDownInput, timeout=300)
def compose_down(*, input_data: ComposeDownInput) -> ToolResult:
    """Tear down services via Docker Compose (optionally remove volumes/orphans)."""
    with span(
        "wrapper.compose.down",
        project_dir=input_data.project_dir,
        file=bool(input_data.file),
        volumes=input_data.volumes,
        remove_orphans=input_data.remove_orphans,
        project_name=input_data.project_name,
    ):
        ex = ComposeExecutor(project_dir=input_data.project_dir)
        return ex.down_result(
            project_dir=input_data.project_dir,
            file=input_data.file,
            volumes=input_data.volumes,
            remove_orphans=input_data.remove_orphans,
            project_name=input_data.project_name,
            timeout=input_data.timeout,
        )


@tool("compose.ps", ComposePsInput, timeout=120)
def compose_ps(*, input_data: ComposePsInput) -> ToolResult:
    """
    List services. Tries `--format json` first; falls back to plain text when unsupported.
    """
    with span(
        "wrapper.compose.ps",
        project_dir=input_data.project_dir,
        file=bool(input_data.file),
        project_name=input_data.project_name,
    ):
        ex = ComposeExecutor(project_dir=input_data.project_dir)
        res = ex.ps_result(
            project_dir=input_data.project_dir,
            file=input_data.file,
            project_name=input_data.project_name,
            timeout=input_data.timeout,
        )
        return _ensure_json_meta(res)


@tool("compose.logs", ComposeLogsInput, timeout=0)  # 0 means “let executor decide”
def compose_logs(*, input_data: ComposeLogsInput) -> ToolResult:
    """
    Fetch service logs. If follow=True, consider providing a timeout at call time.
    """
    with span(
        "wrapper.compose.logs",
        project_dir=input_data.project_dir,
        project_name=input_data.project_name,
        services=len(input_data.services or []),
        tail=input_data.tail,
        timestamps=input_data.timestamps,
        follow=input_data.follow,
    ):
        ex = ComposeExecutor(project_dir=input_data.project_dir)
        return ex.logs_result(
            project_dir=input_data.project_dir,
            services=input_data.services,
            file=input_data.file,
            project_name=input_data.project_name,
            tail=input_data.tail,
            timestamps=input_data.timestamps,
            follow=input_data.follow,
            timeout=input_data.timeout,
        )
