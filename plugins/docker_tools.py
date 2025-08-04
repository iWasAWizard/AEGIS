# aegis/plugins/docker_tools.py
"""
Tools for interacting with the Docker daemon on the host machine.
"""
import json

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.docker_exec import DockerExecutor
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# --- Input Models ---


class ListContainersInput(BaseModel):
    """Input model for listing Docker containers. Takes no arguments."""

    pass


class InspectContainerInput(BaseModel):
    """Input model for inspecting a specific Docker container.

    :ivar container_id: The ID or name of the container to inspect.
    :vartype container_id: str
    """

    container_id: str = Field(
        ..., description="The ID or name of the container to inspect."
    )


# --- Tools ---


@register_tool(
    name="docker_list_containers",
    input_model=ListContainersInput,
    description="Lists all running Docker containers on the host machine.",
    category="docker",
    tags=["docker", "native", "system"],
    safe_mode=True,
)
def docker_list_containers(input_data: ListContainersInput) -> str:
    """
    Uses the DockerExecutor to get a list of running containers.

    :param input_data: An empty input model.
    :type input_data: ListContainersInput
    :return: A formatted string listing the running containers.
    :rtype: str
    """
    logger.info("Executing tool: docker_list_containers")
    try:
        executor = DockerExecutor()
        return executor.list_containers()
    except Exception as e:
        logger.exception("docker_list_containers tool failed during execution.")
        # Re-raise as a ToolExecutionError so the agent gets a clean error message.
        raise ToolExecutionError(f"Failed to list Docker containers: {e}")


@register_tool(
    name="docker_inspect_container",
    input_model=InspectContainerInput,
    description="Returns detailed information about a specific container in JSON format.",
    category="docker",
    tags=["docker", "native", "system"],
    safe_mode=True,
)
def docker_inspect_container(input_data: InspectContainerInput) -> str:
    """
    Uses the DockerExecutor to get detailed information about a container.

    :param input_data: The validated input data for the tool, containing the container_id.
    :type input_data: InspectContainerInput
    :return: A JSON string containing the detailed container information.
    :rtype: str
    """
    logger.info(
        f"Executing tool: docker_inspect_container on '{input_data.container_id}'"
    )
    try:
        executor = DockerExecutor()
        inspection_data = executor.inspect_container(input_data.container_id)
        return json.dumps(inspection_data, indent=2, default=str)
    except Exception as e:
        logger.exception(
            f"docker_inspect_container tool failed for '{input_data.container_id}'."
        )
        raise ToolExecutionError(
            f"Failed to inspect container '{input_data.container_id}': {e}"
        )
