# aegis/tools/wrappers/docker.py
from __future__ import annotations

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field

from aegis.registry import tool
from aegis.schemas.tool_result import ToolResult
from aegis.executors.docker_exec import DockerExecutor
from aegis.utils.tracing import span  # observability

# Read-only helpers use the Docker SDK directly
try:
    import docker  # type: ignore
    from docker.errors import DockerException  # type: ignore
except Exception:  # pragma: no cover - optional import; errors handled in tools
    docker = None
    DockerException = Exception


# ---------- Input models ----------


class DockerPullInput(BaseModel):
    image: str = Field(
        ..., description="Repository name, e.g. 'nginx' or 'nginx:latest'"
    )
    tag: str = Field(
        default="latest", description="Tag to pull if not included in image"
    )
    auth_username: Optional[str] = Field(
        default=None, description="Registry username (optional)"
    )
    auth_password: Optional[str] = Field(
        default=None, description="Registry password (optional)"
    )
    registry: Optional[str] = Field(
        default=None, description="Registry server, e.g. 'registry-1.docker.io'"
    )


class DockerRunInput(BaseModel):
    image: str = Field(..., description="Image, e.g. 'nginx:latest'")
    name: Optional[str] = Field(default=None, description="Optional container name")
    command: Optional[Union[List[str], str]] = Field(
        default=None, description="Override CMD/ENTRYPOINT"
    )
    environment: Optional[Union[Dict[str, str], List[str]]] = Field(
        default=None, description="Dict or list of 'KEY=VALUE'"
    )
    ports: Optional[Union[Dict[str, int], List[str]]] = Field(
        default=None,
        description="Dict like {'80/tcp': 8080} or list like ['8080:80/tcp']",
    )
    volumes: Optional[List[str]] = Field(
        default=None, description="Bind mounts in 'host_path:container_path[:ro|rw]'"
    )
    detach: bool = Field(default=True, description="Run in background")
    remove: bool = Field(default=False, description="Auto-remove on stop")
    workdir: Optional[str] = Field(
        default=None, description="Working directory inside container"
    )
    user: Optional[str] = Field(default=None, description="User to run as")


class DockerStopInput(BaseModel):
    container_id: str = Field(..., description="Container ID or name")
    timeout: int = Field(default=10, description="Stop timeout (seconds)")


class DockerExecInput(BaseModel):
    container_id: str = Field(..., description="Container ID or name")
    command: List[str] = Field(
        ..., description="Command vector, e.g. ['sh','-lc','echo hi']"
    )
    workdir: Optional[str] = Field(
        default=None, description="Working directory in container"
    )
    user: Optional[str] = Field(default=None, description="User to run as")
    env: Optional[Union[Dict[str, str], List[str]]] = Field(
        default=None, description="Env dict or list of 'KEY=VALUE'"
    )
    detach: bool = Field(default=False, description="Detach exec (stream not captured)")
    tty: bool = Field(default=False, description="Allocate TTY")


class DockerCopyToInput(BaseModel):
    container_id: str = Field(..., description="Container ID or name")
    src_path: str = Field(..., description="Host file/dir path")
    dest_path: str = Field(..., description="Destination path inside container")


class DockerCopyFromInput(BaseModel):
    container_id: str = Field(..., description="Container ID or name")
    src_path: str = Field(..., description="Path inside container (file or dir)")
    dest_path: str = Field(..., description="Destination path on host (directory)")


# Discovery / inspection inputs


class DockerListContainersInput(BaseModel):
    all: bool = Field(default=False, description="Include stopped containers")
    status: Optional[str] = Field(
        default=None,
        description="Optional status filter: created|restarting|running|removing|paused|exited|dead",
    )
    name_prefix: Optional[str] = Field(
        default=None, description="Filter: container name starts with this prefix"
    )
    label: Optional[str] = Field(
        default=None, description="Filter by label 'key' or 'key=value'"
    )


class DockerInspectContainerInput(BaseModel):
    container_id: str = Field(..., description="Container ID or name")


class DockerInspectImageInput(BaseModel):
    image: str = Field(..., description="Image reference (name:tag or ID)")


# ---------- Tool shims (return ToolResult) ----------


@tool("docker.pull", DockerPullInput, timeout=600)
def docker_pull(*, input_data: DockerPullInput) -> ToolResult:
    """
    Pull a Docker image (with optional registry auth).
    """
    with span(
        "wrapper.docker.pull",
        image=input_data.image,
        tag=input_data.tag,
        registry=bool(input_data.registry),
        authed=bool(input_data.auth_username or input_data.auth_password),
    ):
        ex = DockerExecutor()
        return ex.pull_image_result(
            name=input_data.image,
            tag=input_data.tag,
            auth_username=input_data.auth_username,
            auth_password=input_data.auth_password,
            registry=input_data.registry,
        )


@tool(
    "docker.run", DockerRunInput, timeout=0
)  # 0: let executor manage long/interactive runs
def docker_run(*, input_data: DockerRunInput) -> ToolResult:
    """
    Run a container. Supports env, ports, volumes, detach/remove, workdir, user.
    """
    with span(
        "wrapper.docker.run",
        image=input_data.image,
        name=input_data.name,
        detach=input_data.detach,
        remove=input_data.remove,
    ):
        ex = DockerExecutor()
        return ex.run_container_result(
            image=input_data.image,
            name=input_data.name,
            command=input_data.command,
            environment=input_data.environment,
            ports=input_data.ports,
            volumes=input_data.volumes,
            detach=input_data.detach,
            remove=input_data.remove,
            workdir=input_data.workdir,
            user=input_data.user,
        )


@tool("docker.stop", DockerStopInput, timeout=60)
def docker_stop(*, input_data: DockerStopInput) -> ToolResult:
    """
    Stop a running container by ID or name.
    """
    with span("wrapper.docker.stop", container_id=input_data.container_id):
        ex = DockerExecutor()
        return ex.stop_container_result(
            container_id=input_data.container_id,
            timeout=input_data.timeout,
        )


@tool("docker.exec", DockerExecInput, timeout=0)
def docker_exec(*, input_data: DockerExecInput) -> ToolResult:
    """
    Execute a command inside a running container.
    """
    with span(
        "wrapper.docker.exec",
        container_id=input_data.container_id,
        workdir=input_data.workdir,
        tty=input_data.tty,
        detach=input_data.detach,
    ):
        ex = DockerExecutor()
        return ex.exec_in_container_result(
            container_id=input_data.container_id,
            command=input_data.command,
            workdir=input_data.workdir,
            user=input_data.user,
            env=input_data.env,
            detach=input_data.detach,
            tty=input_data.tty,
        )


@tool("docker.cp.to", DockerCopyToInput, timeout=120)
def docker_copy_to(*, input_data: DockerCopyToInput) -> ToolResult:
    """
    Copy a file or directory from host into a container.
    """
    with span(
        "wrapper.docker.cp.to",
        container_id=input_data.container_id,
        src=input_data.src_path,
        dest=input_data.dest_path,
    ):
        ex = DockerExecutor()
        return ex.copy_to_container_result(
            container_id=input_data.container_id,
            src_path=input_data.src_path,
            dest_path=input_data.dest_path,
        )


@tool("docker.cp.from", DockerCopyFromInput, timeout=120)
def docker_copy_from(*, input_data: DockerCopyFromInput) -> ToolResult:
    """
    Copy a file or directory from a container to the host.
    """
    with span(
        "wrapper.docker.cp.from",
        container_id=input_data.container_id,
        src=input_data.src_path,
        dest=input_data.dest_path,
    ):
        ex = DockerExecutor()
        return ex.copy_from_container_result(
            container_id=input_data.container_id,
            src_path=input_data.src_path,
            dest_path=input_data.dest_path,
        )


# ---------- Discovery / inspection tools (read-only, SDK direct) ----------


def _toolresult_from_json(payload: object, *, tool_name: str) -> ToolResult:
    """
    Build a ToolResult with JSON in stdout, success=True, exit_code=0.
    This keeps parity with other tools while using the SDK directly.
    """
    import json as _json

    return ToolResult(
        success=True,
        stdout=_json.dumps(payload, indent=2, default=str),
        stderr="",
        exit_code=0,
        tool_name=tool_name,
        truncated={"stdout": False, "stderr": False},
        meta={"format": "json"},
    )


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


@tool("docker.list.containers", DockerListContainersInput, timeout=30)
def docker_list_containers(*, input_data: DockerListContainersInput) -> ToolResult:
    """
    List containers with optional filters. Returns JSON array of summaries:
    [{id, name, image, status, state, labels, created, ports}]
    """
    with span(
        "wrapper.docker.list",
        all=input_data.all,
        status=input_data.status,
        name_prefix=bool(input_data.name_prefix),
        label=bool(input_data.label),
    ):
        if docker is None:
            return ToolResult(
                success=False,
                stdout="",
                stderr="docker SDK not available; install 'docker' Python package",
                exit_code=1,
                tool_name="docker.list.containers",
            )

        try:
            client = docker.from_env()
            filters = {}
            if input_data.status:
                filters["status"] = input_data.status
            if input_data.label:
                filters["label"] = input_data.label

            containers = client.containers.list(
                all=input_data.all, filters=filters or None
            )

            results = []
            for c in containers:
                # name: first name without leading slash
                nm = None
                try:
                    nm = (c.name or (c.attrs.get("Name") or "")).lstrip("/")
                except Exception:
                    pass

                if (
                    input_data.name_prefix
                    and nm
                    and not nm.startswith(input_data.name_prefix)
                ):
                    continue

                info = {
                    "id": c.id,
                    "name": nm,
                    "image": getattr(c.image, "tags", None)
                    or getattr(c.image, "short_id", None),
                    "status": getattr(c, "status", None),
                    "state": (getattr(c, "attrs", {}) or {}).get("State"),
                    "labels": (
                        getattr(c, "labels", None)
                        or (getattr(c, "attrs", {}) or {})
                        .get("Config", {})
                        .get("Labels")
                    ),
                    "created": (getattr(c, "attrs", {}) or {}).get("Created"),
                    "ports": (getattr(c, "attrs", {}) or {})
                    .get("NetworkSettings", {})
                    .get("Ports"),
                }
                results.append(info)

            return _toolresult_from_json(results, tool_name="docker.list.containers")
        except DockerException as e:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"Docker API error: {e}",
                exit_code=1,
                tool_name="docker.list.containers",
            )


@tool("docker.inspect.container", DockerInspectContainerInput, timeout=30)
def docker_inspect_container(*, input_data: DockerInspectContainerInput) -> ToolResult:
    """
    Inspect a container by ID or name. Returns the full inspect JSON.
    """
    with span("wrapper.docker.inspect.container", container_id=input_data.container_id):
        if docker is None:
            return ToolResult(
                success=False,
                stdout="",
                stderr="docker SDK not available; install 'docker' Python package",
                exit_code=1,
                tool_name="docker.inspect.container",
            )
        try:
            client = docker.from_env()
            container = client.containers.get(input_data.container_id)
            # attrs already mirrors 'docker inspect' JSON
            return _toolresult_from_json(
                container.attrs, tool_name="docker.inspect.container"
            )
        except DockerException as e:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"Docker API error: {e}",
                exit_code=1,
                tool_name="docker.inspect.container",
            )


@tool("docker.inspect.image", DockerInspectImageInput, timeout=30)
def docker_inspect_image(*, input_data: DockerInspectImageInput) -> ToolResult:
    """
    Inspect an image by name:tag or ID. Returns the full inspect JSON.
    """
    with span("wrapper.docker.inspect.image", image=input_data.image):
        if docker is None:
            return ToolResult(
                success=False,
                stdout="",
                stderr="docker SDK not available; install 'docker' Python package",
                exit_code=1,
                tool_name="docker.inspect.image",
            )
        try:
            client = docker.from_env()
            image = client.images.get(input_data.image)
            # image.attrs is also 'docker inspect' JSON
            return _toolresult_from_json(image.attrs, tool_name="docker.inspect.image")
        except DockerException as e:
            return ToolResult(
                success=False,
                stdout="",
                stderr=f"Docker API error: {e}",
                exit_code=1,
                tool_name="docker.inspect.image",
            )
