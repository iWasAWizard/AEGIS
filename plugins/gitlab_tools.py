# aegis/plugins/gitlab_tools.py
"""
Tools for interacting with a GitLab instance via its API.
"""
import json

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.gitlab_exec import GitlabExecutor
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# --- Input Models ---


class ListProjectsInput(BaseModel):
    """Input model for listing GitLab projects. Takes no arguments."""

    pass


class CreateIssueInput(BaseModel):
    """Input model for creating a new GitLab issue.

    :ivar project_id: The numeric ID of the project where the issue will be created.
    :vartype project_id: int
    :ivar title: The title of the issue.
    :vartype title: str
    :ivar description: The main content/body of the issue.
    :vartype description: str
    """

    project_id: int = Field(
        ...,
        description="The numeric ID of the project where the issue will be created.",
    )
    title: str = Field(..., description="The title of the issue.")
    description: str = Field(
        ..., description="The main content/body of the issue. Supports Markdown."
    )


# --- Tools ---


@register_tool(
    name="gitlab_list_projects",
    input_model=ListProjectsInput,
    description="Lists all projects the authenticated user has access to on GitLab.",
    category="gitlab",
    tags=["gitlab", "native", "devops"],
    safe_mode=True,
)
def gitlab_list_projects(input_data: ListProjectsInput) -> str:
    """
    Uses the GitlabExecutor to get a list of accessible projects.

    :param input_data: An empty input model.
    :type input_data: ListProjectsInput
    :return: A formatted string listing the projects.
    :rtype: str
    """
    logger.info("Executing tool: gitlab_list_projects")
    try:
        executor = GitlabExecutor()
        return executor.list_projects()
    except Exception as e:
        logger.exception("gitlab_list_projects tool failed during execution.")
        raise ToolExecutionError(f"Failed to list GitLab projects: {e}")


@register_tool(
    name="gitlab_create_issue",
    input_model=CreateIssueInput,
    description="Creates a new issue in a specified GitLab project.",
    category="gitlab",
    tags=["gitlab", "native", "devops"],
    safe_mode=True,
)
def gitlab_create_issue(input_data: CreateIssueInput) -> str:
    """
    Uses the GitlabExecutor to create a new issue in a project.

    :param input_data: The validated input data for the tool.
    :type input_data: CreateIssueInput
    :return: A JSON string containing the result of the issue creation.
    :rtype: str
    """
    logger.info(
        f"Executing tool: gitlab_create_issue in project '{input_data.project_id}'"
    )
    try:
        executor = GitlabExecutor()
        result_data = executor.create_issue(
            project_id=input_data.project_id,
            title=input_data.title,
            description=input_data.description,
        )
        return json.dumps(result_data, indent=2)
    except Exception as e:
        logger.exception(
            f"gitlab_create_issue tool failed for project '{input_data.project_id}'."
        )
        raise ToolExecutionError(
            f"Failed to create issue in project '{input_data.project_id}': {e}"
        )
