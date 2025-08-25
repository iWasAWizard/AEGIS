# aegis/tools/wrappers/gitlab.py
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field

from aegis.registry import tool
from aegis.schemas.tool_result import ToolResult
from aegis.executors.gitlab_exec import GitlabExecutor
from aegis.utils.tracing import span  # observability


# ---------- Input models ----------


class GitlabListProjectsInput(BaseModel):
    search: Optional[str] = Field(
        default=None, description="Search query for project names/paths"
    )
    visibility: Optional[str] = Field(
        default=None,
        description="Optional visibility filter: public|internal|private",
    )


class GitlabCreateIssueInput(BaseModel):
    project_id: int = Field(..., description="Numeric project ID")
    title: str = Field(..., description="Issue title")
    description: Optional[str] = Field(default=None, description="Issue description")
    labels: Optional[List[str]] = Field(
        default=None, description="List of labels to apply"
    )


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


# ---------- Tools ----------


@tool(
    "gitlab.list.projects",
    GitlabListProjectsInput,
    timeout=30,
    description="List GitLab projects (optionally filtered by search and visibility).",
    category="gitlab",
    tags=("gitlab", "projects", "read-only"),
)
def gitlab_list_projects(*, input_data: GitlabListProjectsInput) -> ToolResult:
    """
    List projects from GitLab via GitlabExecutor.
    Returns ToolResult with JSON/text in stdout and useful metadata in meta.
    """
    with span(
        "wrapper.gitlab.list",
        search=bool(input_data.search),
        visibility=input_data.visibility,
    ):
        ex = GitlabExecutor()
        res = ex.list_projects_result(
            search=input_data.search,
            visibility=input_data.visibility,
        )
        return _ensure_json_meta(res)


@tool(
    "gitlab.create.issue",
    GitlabCreateIssueInput,
    timeout=60,
    description="Create a new GitLab issue in the specified project.",
    category="gitlab",
    tags=("gitlab", "issues", "write"),
)
def gitlab_create_issue(*, input_data: GitlabCreateIssueInput) -> ToolResult:
    """
    Create an issue in GitLab via GitlabExecutor.
    Returns ToolResult with API response text (or dry-run preview) in stdout.
    """
    with span("wrapper.gitlab.create", project_id=input_data.project_id):
        ex = GitlabExecutor()
        res = ex.create_issue_result(
            project_id=input_data.project_id,
            title=input_data.title,
            description=input_data.description,
            labels=input_data.labels,
        )
        return _ensure_json_meta(res)
