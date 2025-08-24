# aegis/executors/gitlab_exec.py
"""
Provides a client for executing GitLab operations via the python-gitlab SDK.
"""
from typing import List, Dict, Any

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.schemas.settings import settings
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log
import time
import json
from aegis.utils.exec_common import (
    now_ms as _common_now_ms,
    map_exception_to_error_type as _common_map_error,
)

logger = setup_logger(__name__)

try:
    import gitlab
    from gitlab.exceptions import GitlabError

    GITLAB_SDK_AVAILABLE = True
except ImportError:
    GITLAB_SDK_AVAILABLE = False


class GitlabExecutor:
    """A client for managing and executing GitLab API commands."""

    def __init__(self):
        if not GITLAB_SDK_AVAILABLE:
            raise ToolExecutionError("The 'python-gitlab' library is not installed.")

        url = settings.GITLAB_URL
        token = settings.GITLAB_PRIVATE_TOKEN

        if not url or not token:
            raise ConfigurationError(
                "GITLAB_URL and GITLAB_PRIVATE_TOKEN must be set in the environment or .env file."
            )

        try:
            self.gl = gitlab.Gitlab(url, private_token=token, timeout=30)
            self.gl.auth()
            logger.info("Successfully authenticated with GitLab.")
        except GitlabError as e:
            logger.error(f"Failed to authenticate to GitLab: {e}")
            raise ToolExecutionError(f"Failed to authenticate to GitLab: {e}")

    def list_projects(
        self, search: str | None = None, visibility: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        List GitLab projects optionally filtered by search term and visibility.

        :param search: Optional search query for project names/paths.
        :type search: Optional[str]
        :param visibility: Optional visibility filter ("public", "internal", "private").
        :type visibility: Optional[str]
        :return: A list of project dicts.
        :rtype: List[Dict[str, Any]]
        """
        try:
            kwargs = {}
            if search:
                kwargs["search"] = search
            if visibility:
                kwargs["visibility"] = visibility

            projects = self.gl.projects.list(all=True, **kwargs)
            results = []
            for p in projects:
                try:
                    results.append(
                        {
                            "id": p.id,
                            "name": p.name,
                            "path_with_namespace": p.path_with_namespace,
                            "visibility": p.visibility,
                            "web_url": p.web_url,
                            "last_activity_at": p.last_activity_at,
                        }
                    )
                except Exception:
                    continue
            return results
        except GitlabError as e:
            raise ToolExecutionError(f"GitLab API error (list projects): {e}") from e
        except Exception as e:
            raise ToolExecutionError(f"GitLab error (list projects): {e}") from e

    def create_issue(
        self,
        project_id: int,
        title: str,
        description: str | None = None,
        labels: list[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Create an issue in a GitLab project.

        :param project_id: The numeric project ID.
        :type project_id: int
        :param title: Issue title.
        :type title: str
        :param description: Optional issue description.
        :type description: Optional[str]
        :param labels: Optional list of labels.
        :type labels: Optional[List[str]]
        :return: Created issue information.
        :rtype: Dict[str, Any]
        """
        try:
            proj = self.gl.projects.get(project_id)
            payload: Dict[str, Any] = {"title": title}
            if description:
                payload["description"] = description
            if labels:
                payload["labels"] = labels

            issue = proj.issues.create(payload)
            return {
                "iid": issue.iid,
                "title": issue.title,
                "state": issue.state,
                "web_url": issue.web_url,
                "created_at": issue.created_at,
            }
        except GitlabError as e:
            raise ToolExecutionError(f"GitLab API error (create issue): {e}") from e
        except Exception as e:
            raise ToolExecutionError(f"GitLab error (create issue): {e}") from e


# === ToolResult wrappers ===
def _now_ms() -> int:
    # Delegate to shared clock for consistency/testability
    return _common_now_ms()


def _error_type_from_exception(e: Exception) -> str:
    """
    Preserve existing labels while consulting the shared mapper for consistency.
    """
    msg = str(e).lower()
    mapped = (_common_map_error(e) or "").lower()
    if "timeout" in msg or mapped == "timeout":
        return "Timeout"
    if "permission" in msg or "auth" in msg or mapped == "permission_denied":
        return "Auth"
    if "not found" in msg or "no such" in msg or mapped == "not_found":
        return "NotFound"
    if "parse" in msg or "json" in msg:
        return "Parse"
    return "Runtime"


class GitlabExecutorToolResultMixin:
    def list_projects_result(
        self, search: str | None = None, visibility: str | None = None
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="gitlab.list_projects",
                args=redact_for_log({"search": search, "visibility": visibility}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] gitlab.list_projects",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.list_projects(search=search, visibility=visibility)
            return ToolResult.ok_result(
                stdout=json.dumps(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"search": search, "visibility": visibility},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"search": search, "visibility": visibility},
            )

    def create_issue_result(
        self,
        project_id: int,
        title: str,
        description: str | None = None,
        labels: list[str] | None = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="gitlab.create_issue",
                args=redact_for_log({"project_id": project_id, "title": title}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] gitlab.create_issue",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            out = self.create_issue(
                project_id=project_id,
                title=title,
                description=description,
                labels=labels,
            )
            return ToolResult.ok_result(
                stdout=json.dumps(out),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"project_id": project_id, "title": title},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_error_type_from_exception(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"project_id": project_id, "title": title},
            )


GitlabExecutor.list_projects_result = GitlabExecutorToolResultMixin.list_projects_result
GitlabExecutor.create_issue_result = GitlabExecutorToolResultMixin.create_issue_result
