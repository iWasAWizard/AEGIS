# aegis/executors/gitlab_exec.py
"""
Provides a client for executing GitLab operations via the python-gitlab SDK.
"""
from typing import List, Dict, Any

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.schemas.settings import settings
from aegis.utils.logger import setup_logger

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
            self.gl = gitlab.Gitlab(url, private_token=token)
            self.gl.auth()  # Verify authentication
            logger.info(f"Successfully connected to GitLab instance at {url}")
        except GitlabError as e:
            logger.error(f"Failed to authenticate with GitLab at {url}: {e}")
            raise ConfigurationError(f"Failed to authenticate with GitLab: {e}")

    def list_projects(self) -> str:
        """Lists all projects accessible by the authenticated user."""
        try:
            projects = self.gl.projects.list(get_all=True)
            if not projects:
                return "No accessible projects found."

            output = ["Accessible GitLab Projects:"]
            for project in projects:
                output.append(
                    f"  - ID: {project.id}, Name: {project.name_with_namespace}, URL: {project.web_url}"
                )
            return "\n".join(output)
        except GitlabError as e:
            logger.error(f"GitLab API error while listing projects: {e}")
            raise ToolExecutionError(f"GitLab API error: {e}")

    def create_issue(
        self, project_id: int, title: str, description: str
    ) -> Dict[str, Any]:
        """Creates an issue in a specific project."""
        try:
            project = self.gl.projects.get(project_id)
            issue = project.issues.create({"title": title, "description": description})
            logger.info(
                f"Successfully created issue #{issue.iid} in project {project.name_with_namespace}"
            )
            return {
                "message": "Issue created successfully.",
                "project_id": project.id,
                "issue_id": issue.iid,
                "issue_url": issue.web_url,
            }
        except GitlabError as e:
            logger.error(f"GitLab API error while creating issue: {e}")
            raise ToolExecutionError(f"GitLab API error: {e}")
