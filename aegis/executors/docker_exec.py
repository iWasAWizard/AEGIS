# aegis/executors/docker_exec.py
"""
Docker executor with log redaction and ToolResult wrappers.

Requires: docker (python SDK)
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import io
import tarfile
import json
import time
import re

from aegis.exceptions import ToolExecutionError, ConfigurationError
from aegis.utils.logger import setup_logger
from aegis.schemas.tool_result import ToolResult
from aegis.utils.dryrun import dry_run
from aegis.utils.redact import redact_for_log

logger = setup_logger(__name__)

try:
    import docker
    from docker.errors import APIError, DockerException, ImageNotFound, NotFound

    DOCKER_AVAILABLE = True
except Exception:
    DOCKER_AVAILABLE = False


def _sanitize_env(env: Dict[str, str] | List[str] | None) -> Any:
    """
    Convert env into a display-friendly structure and redact sensitive values.
    - Accepts dict or list of 'KEY=VAL'
    """
    if env is None:
        return None
    if isinstance(env, dict):
        return redact_for_log(env)
    if isinstance(env, list):
        out = {}
        for item in env:
            try:
                if "=" in item:
                    k, v = item.split("=", 1)
                    out[k] = v
            except Exception:
                continue
        return redact_for_log(out)
    return env


def _sanitize_auth(auth_config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not auth_config:
        return None
    return redact_for_log(auth_config)


class DockerExecutor:
    """Lightweight wrapper around docker SDK with safer logging."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        :param base_url: Optional Docker daemon URL (e.g., unix:///var/run/docker.sock)
        :param timeout: API client timeout (seconds)
        """
        if not DOCKER_AVAILABLE:
            raise ConfigurationError("The 'docker' Python SDK is not installed.")
        try:
            self.client = (
                docker.from_env(timeout=timeout)
                if base_url is None
                else docker.DockerClient(base_url=base_url, timeout=timeout)
            )
            # sanity check
            self.client.ping()
            logger.info("Connected to Docker daemon")
        except DockerException as e:
            raise ToolExecutionError(f"Docker connection error: {e}") from e

    # --- Core ops ---

    def pull_image(
        self,
        name: str,
        tag: str = "latest",
        auth_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            img = self.client.images.pull(
                repository=name, tag=tag, auth_config=auth_config
            )
            return img.id
        except ImageNotFound as e:
            raise ToolExecutionError(f"Docker image not found: {name}:{tag}") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error (pull): {e}") from e

    def run_container(
        self,
        image: str,
        *,
        name: Optional[str] = None,
        command: Optional[List[str] | str] = None,
        environment: Optional[Dict[str, str] | List[str]] = None,
        detach: bool = True,
        auto_remove: bool = False,
        network: Optional[str] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        ports: Optional[Dict[str, int | str]] = None,
        user: Optional[str] = None,
        working_dir: Optional[str] = None,
    ) -> str:
        try:
            cont = self.client.containers.run(
                image=image,
                name=name,
                command=command,
                environment=environment,
                detach=detach,
                auto_remove=auto_remove,
                network=network,
                volumes=volumes,
                ports=ports,
                user=user,
                working_dir=working_dir,
                tty=False,
                stdin_open=False,
            )
            return cont.id
        except NotFound as e:
            raise ToolExecutionError(f"Image or resource not found: {image}") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error (run): {e}") from e

    def stop_container(self, container_id_or_name: str, timeout: int = 10) -> bool:
        try:
            cont = self.client.containers.get(container_id_or_name)
            cont.stop(timeout=timeout)
            return True
        except NotFound:
            return False
        except APIError as e:
            raise ToolExecutionError(f"Docker API error (stop): {e}") from e

    def exec_in_container(
        self,
        container_id_or_name: str,
        cmd: List[str] | str,
        timeout: Optional[int] = None,
    ) -> Tuple[int, str]:
        try:
            cont = self.client.containers.get(container_id_or_name)
            rc, output = cont.exec_run(cmd, tty=False, demux=False, stream=False)
            # docker SDK returns combined bytes; normalize to str
            text = (
                output.decode("utf-8", "ignore")
                if isinstance(output, (bytes, bytearray))
                else str(output)
            )
            return (int(rc) if rc is not None else 0, text)
        except NotFound as e:
            raise ToolExecutionError("Container not found") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error (exec): {e}") from e

    def copy_to_container(
        self, container_id_or_name: str, src_path: str, dest_path: str
    ) -> bool:
        """
        Copy a single file to container using put_archive.
        """
        try:
            cont = self.client.containers.get(container_id_or_name)
            data = Path(src_path).read_bytes()
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tarf:
                info = tarfile.TarInfo(name=Path(dest_path).name)
                info.size = len(data)
                info.mtime = time.time()
                tarf.addfile(info, io.BytesIO(data))
            tar_stream.seek(0)
            cont.put_archive(path=str(Path(dest_path).parent), data=tar_stream.read())
            return True
        except Exception as e:
            raise ToolExecutionError(f"Docker copy_to_container error: {e}") from e

    def copy_from_container(
        self, container_id_or_name: str, src_path: str, dest_path: str
    ) -> bool:
        """
        Copy file/dir from container using get_archive.
        """
        try:
            cont = self.client.containers.get(container_id_or_name)
            stream, _ = cont.get_archive(src_path)
            tar_bytes = b"".join(stream)
            with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*") as tarf:
                member = tarf.getmember(Path(src_path).name)
                with tarf.extractfile(member) as fsrc:
                    Path(dest_path).write_bytes(fsrc.read())
            return True
        except Exception as e:
            raise ToolExecutionError(f"Docker copy_from_container error: {e}") from e


# === ToolResult wrappers ===


def _now_ms() -> int:
    return int(time.time() * 1000)


def _errtype(e: Exception) -> str:
    m = str(e).lower()
    if "timeout" in m:
        return "Timeout"
    if "auth" in m or "permission" in m or "denied" in m:
        return "Auth"
    if "not found" in m or "no such" in m:
        return "NotFound"
    if "parse" in m or "json" in m:
        return "Parse"
    return "Runtime"


class DockerExecutorToolResultMixin:
    def pull_image_result(
        self,
        name: str,
        tag: str = "latest",
        auth_config: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.pull",
                args=redact_for_log({"name": name, "tag": tag, "auth": auth_config}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.pull",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            img_id = self.pull_image(name=name, tag=tag, auth_config=auth_config)
            return ToolResult.ok_result(
                stdout=img_id,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"name": name, "tag": tag},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"name": name, "tag": tag},
            )

    def run_container_result(
        self,
        image: str,
        *,
        name: Optional[str] = None,
        command: Optional[List[str] | str] = None,
        environment: Optional[Dict[str, str] | List[str]] = None,
        detach: bool = True,
        auto_remove: bool = False,
        network: Optional[str] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        ports: Optional[Dict[str, int | str]] = None,
        user: Optional[str] = None,
        working_dir: Optional[str] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview_args = {
                "image": image,
                "name": name,
                "command": command,
                "environment": _sanitize_env(environment),
                "network": network,
                "volumes": volumes,
                "ports": ports,
                "user": user,
                "working_dir": working_dir,
            }
            preview = dry_run.preview_payload(
                tool="docker.run", args=redact_for_log(preview_args)
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.run",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            cid = self.run_container(
                image=image,
                name=name,
                command=command,
                environment=environment,
                detach=detach,
                auto_remove=auto_remove,
                network=network,
                volumes=volumes,
                ports=ports,
                user=user,
                working_dir=working_dir,
            )
            return ToolResult.ok_result(
                stdout=cid,
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"image": image, "name": name},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"image": image, "name": name},
            )

    def stop_container_result(
        self, container_id_or_name: str, timeout: int = 10
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.stop",
                args=redact_for_log(
                    {"container": container_id_or_name, "timeout": timeout}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.stop",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            ok = self.stop_container(
                container_id_or_name=container_id_or_name, timeout=timeout
            )
            return ToolResult.ok_result(
                stdout=str(ok),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"container": container_id_or_name},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"container": container_id_or_name},
            )

    def exec_in_container_result(
        self,
        container_id_or_name: str,
        cmd: List[str] | str,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.exec",
                args=redact_for_log({"container": container_id_or_name, "cmd": cmd}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.exec",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            rc, out = self.exec_in_container(
                container_id_or_name=container_id_or_name, cmd=cmd, timeout=timeout
            )
            return ToolResult.ok_result(
                stdout=out,
                exit_code=int(rc),
                latency_ms=_now_ms() - start,
                meta={"container": container_id_or_name},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"container": container_id_or_name},
            )

    def copy_to_container_result(
        self, container_id_or_name: str, src_path: str, dest_path: str
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.cp_to",
                args=redact_for_log(
                    {
                        "container": container_id_or_name,
                        "src": src_path,
                        "dest": dest_path,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.cp_to",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            ok = self.copy_to_container(
                container_id_or_name=container_id_or_name,
                src_path=src_path,
                dest_path=dest_path,
            )
            return ToolResult.ok_result(
                stdout=str(ok),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"container": container_id_or_name, "dest": dest_path},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"container": container_id_or_name},
            )

    def copy_from_container_result(
        self, container_id_or_name: str, src_path: str, dest_path: str
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.cp_from",
                args=redact_for_log(
                    {
                        "container": container_id_or_name,
                        "src": src_path,
                        "dest": dest_path,
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.cp_from",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            ok = self.copy_from_container(
                container_id_or_name=container_id_or_name,
                src_path=src_path,
                dest_path=dest_path,
            )
            return ToolResult.ok_result(
                stdout=str(ok),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"container": container_id_or_name, "src": src_path},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"container": container_id_or_name},
            )


DockerExecutor.pull_image_result = DockerExecutorToolResultMixin.pull_image_result
DockerExecutor.run_container_result = DockerExecutorToolResultMixin.run_container_result
DockerExecutor.stop_container_result = (
    DockerExecutorToolResultMixin.stop_container_result
)
DockerExecutor.exec_in_container_result = (
    DockerExecutorToolResultMixin.exec_in_container_result
)
DockerExecutor.copy_to_container_result = (
    DockerExecutorToolResultMixin.copy_to_container_result
)
DockerExecutor.copy_from_container_result = (
    DockerExecutorToolResultMixin.copy_from_container_result
)
