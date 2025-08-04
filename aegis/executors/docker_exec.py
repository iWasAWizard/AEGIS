# aegis/executors/docker_exec.py
"""
Provides a client for executing Docker operations via the Docker Engine API.
"""
from typing import List, Dict, Any

from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import docker
    from docker.errors import APIError, DockerException

    DOCKER_SDK_AVAILABLE = True
except ImportError:
    DOCKER_SDK_AVAILABLE = False


class DockerExecutor:
    """A client for managing and executing Docker commands."""

    def __init__(self):
        if not DOCKER_SDK_AVAILABLE:
            raise ToolExecutionError("The 'docker' library is not installed.")
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("Successfully connected to the Docker daemon.")
        except DockerException as e:
            logger.error(
                f"Failed to connect to Docker daemon. Is the Docker socket mounted? Error: {e}"
            )
            raise ToolExecutionError(f"Failed to connect to Docker daemon: {e}")

    def list_containers(self) -> str:
        """Lists all running containers."""
        try:
            containers = self.client.containers.list()
            if not containers:
                return "No running containers found."

            output = ["Running Containers:"]
            for container in containers:
                output.append(
                    f"  - ID: {container.short_id}, Name: {container.name}, Image: {container.image.tags[0] if container.image.tags else 'N/A'}"
                )
            return "\n".join(output)
        except APIError as e:
            logger.error(f"Docker API error while listing containers: {e}")
            raise ToolExecutionError(f"Docker API error: {e}")

    def inspect_container(self, container_id: str) -> Dict[str, Any]:
        """Inspects a single container and returns its raw configuration."""
        try:
            container = self.client.containers.get(container_id)
            return container.attrs
        except APIError as e:
            logger.error(
                f"Docker API error while inspecting container '{container_id}': {e}"
            )
            raise ToolExecutionError(f"Docker API error inspecting container: {e}")
