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
from aegis.utils.exec_common import (
    now_ms as _common_now_ms,
    map_exception_to_error_type as _common_map_error,
)

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
                else:
                    out[item] = ""
            except Exception:
                out["?"] = "?"
        return redact_for_log(out)
    return None


def _sanitize_ports(ports: Dict[str, Any] | List[str] | None) -> Any:
    if ports is None:
        return None
    if isinstance(ports, dict):
        return redact_for_log(ports)
    if isinstance(ports, list):
        return [str(p) for p in ports]
    return None


def _sanitize_auth_config(
    auth_config: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
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
    ) -> None:
        try:
            self.client.images.pull(repository=name, tag=tag, auth_config=auth_config)
            logger.info(
                "docker.pull ok",
                extra={
                    "name": name,
                    "tag": tag,
                    "auth": _sanitize_auth_config(auth_config),
                },
            )
        except ImageNotFound as e:
            raise ToolExecutionError(f"Image not found: {name}:{tag}") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error: {e}") from e
        except DockerException as e:
            raise ToolExecutionError(f"Docker error: {e}") from e

    def run_container(
        self,
        image: str,
        *,
        name: Optional[str] = None,
        command: Optional[str | List[str]] = None,
        environment: Optional[Dict[str, str] | List[str]] = None,
        ports: Optional[Dict[str, Any] | List[str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        detach: bool = True,
        auto_remove: bool = False,
        working_dir: Optional[str] = None,
        user: Optional[str] = None,
        stdin_open: bool = False,
        tty: bool = False,
    ) -> str:
        try:
            container = self.client.containers.run(
                image=image,
                name=name,
                command=command,
                environment=environment,
                ports=ports,
                volumes=volumes,
                detach=detach,
                auto_remove=auto_remove,
                working_dir=working_dir,
                user=user,
                stdin_open=stdin_open,
                tty=tty,
            )
            logger.info(
                "docker.run ok",
                extra={
                    "image": image,
                    "name": name,
                    "env": _sanitize_env(environment),
                    "ports": _sanitize_ports(ports),
                    "volumes": redact_for_log(volumes) if volumes else None,
                    "detach": detach,
                    "auto_remove": auto_remove,
                    "workdir": working_dir,
                    "user": user,
                    "stdin_open": stdin_open,
                    "tty": tty,
                },
            )
            return container.id
        except ImageNotFound as e:
            raise ToolExecutionError(f"Image not found: {image}") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error: {e}") from e
        except DockerException as e:
            raise ToolExecutionError(f"Docker error: {e}") from e

    def stop_container(self, container_id: str, timeout: int = 10) -> None:
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            logger.info(
                "docker.stop ok", extra={"id": container_id, "timeout": timeout}
            )
        except NotFound as e:
            raise ToolExecutionError(f"Container not found: {container_id}") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error: {e}") from e
        except DockerException as e:
            raise ToolExecutionError(f"Docker error: {e}") from e

    def exec_in_container(
        self,
        container_id: str,
        cmd: List[str] | str,
        *,
        workdir: Optional[str] = None,
        user: Optional[str] = None,
    ) -> Tuple[int, str, str]:
        try:
            container = self.client.containers.get(container_id)
            exec_id = self.client.api.exec_create(
                container.id, cmd=cmd, workdir=workdir, user=user
            )
            out = self.client.api.exec_start(exec_id)
            rc = self.client.api.exec_inspect(exec_id).get("ExitCode", 1)
            stdout = (
                out.decode("utf-8", "replace")
                if isinstance(out, (bytes, bytearray))
                else str(out)
            )
            logger.info(
                "docker.exec ok",
                extra={
                    "id": container_id,
                    "cmd": cmd,
                    "cwd": workdir,
                    "user": user,
                    "rc": rc,
                },
            )
            return rc, stdout, "" if rc == 0 else stdout
        except NotFound as e:
            raise ToolExecutionError(f"Container not found: {container_id}") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error: {e}") from e
        except DockerException as e:
            raise ToolExecutionError(f"Docker error: {e}") from e

    def copy_to_container(
        self, container_id: str, src_path: str | Path, dest_path: str | Path
    ) -> None:
        try:
            container = self.client.containers.get(container_id)
            tar_stream = _make_tar_stream(src_path, arcname=Path(dest_path).name)
            self.client.api.put_archive(
                container.id,
                path=str(Path(dest_path).parent),
                data=tar_stream.getvalue(),
            )
            logger.info(
                "docker.cp_to ok",
                extra={
                    "id": container_id,
                    "src": str(src_path),
                    "dest": str(dest_path),
                },
            )
        except NotFound as e:
            raise ToolExecutionError(f"Container not found: {container_id}") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error: {e}") from e
        except DockerException as e:
            raise ToolExecutionError(f"Docker error: {e}") from e

    def copy_from_container(
        self, container_id: str, src_path: str | Path, dest_dir: str | Path
    ) -> Path:
        try:
            container = self.client.containers.get(container_id)
            bits, _ = self.client.api.get_archive(container.id, path=str(src_path))
            _extract_tar_stream(bits, dest_dir)
            dest = Path(dest_dir) / Path(src_path).name
            logger.info(
                "docker.cp_from ok",
                extra={"id": container_id, "src": str(src_path), "dest": str(dest)},
            )
            return dest
        except NotFound as e:
            raise ToolExecutionError(f"Container not found: {container_id}") from e
        except APIError as e:
            raise ToolExecutionError(f"Docker API error: {e}") from e
        except DockerException as e:
            raise ToolExecutionError(f"Docker error: {e}") from e


def _make_tar_stream(src: str | Path, arcname: Optional[str] = None) -> io.BytesIO:
    """
    Pack a file or directory into a tar stream that Docker's put_archive can consume.
    """
    src_path = Path(src)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        if src_path.is_dir():
            for p in src_path.rglob("*"):
                tar.add(
                    p,
                    arcname=str(
                        Path(arcname or src_path.name) / p.relative_to(src_path)
                    ),
                )
        else:
            tar.add(src_path, arcname=arcname or src_path.name)
    stream.seek(0)
    return stream


def _extract_tar_stream(
    bits: bytes | io.BufferedReader | Any, dest_dir: str | Path
) -> None:
    """
    Extracts a tar stream returned by Docker to a destination directory.
    - Accepts bytes, a file-like with .read(), or an **iterable of bytes chunks** (common).
    - Uses a safe extractor to prevent path traversal outside dest_dir.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    # Normalize to bytes
    if hasattr(bits, "read"):
        data = bits.read()
    elif isinstance(bits, (bytes, bytearray)):
        data = bytes(bits)
    else:
        # Iterable / generator of chunks
        data = b"".join(chunk for chunk in bits)

    def _is_within_directory(directory: Path, target: Path) -> bool:
        try:
            directory = directory.resolve()
            target = target.resolve()
            return str(target).startswith(str(directory) + "/") or target == directory
        except Exception:
            return False

    def _safe_extractall(tar_obj: tarfile.TarFile, path: Path) -> None:
        for member in tar_obj.getmembers():
            member_path = path / member.name
            # Prevent absolute paths and traversal
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise ToolExecutionError(f"Unsafe path in tar member: {member.name}")
            # Ensure final resolved path is within destination
            tmp_target = (path / member.name).resolve()
            if not _is_within_directory(path, tmp_target):
                raise ToolExecutionError(
                    f"Refusing to extract outside destination: {member.name}"
                )
        tar_obj.extractall(path=path)

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
        _safe_extractall(tar, dest)


# === ToolResult wrappers ===


def _now_ms() -> int:
    return _common_now_ms()


def _errtype(e: Exception) -> str:
    m = str(e).lower()
    mapped = (_common_map_error(e) or "").lower()
    if "timeout" in m or mapped == "timeout":
        return "Timeout"
    if (
        "auth" in m
        or "permission" in m
        or "denied" in m
        or mapped == "permission_denied"
    ):
        return "Auth"
    if "not found" in m or "no such" in m or mapped == "not_found":
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
                args=redact_for_log(
                    {
                        "name": name,
                        "tag": tag,
                        "auth": _sanitize_auth_config(auth_config),
                    }
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.pull",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            self.pull_image(name=name, tag=tag, auth_config=auth_config)
            return ToolResult.ok_result(
                stdout="ok",
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
        command: Optional[str | List[str]] = None,
        environment: Optional[Dict[str, str] | List[str]] = None,
        ports: Optional[Dict[str, Any] | List[str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        detach: bool = True,
        auto_remove: bool = False,
        working_dir: Optional[str] = None,
        user: Optional[str] = None,
        stdin_open: bool = False,
        tty: bool = False,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.run",
                args=redact_for_log(
                    {
                        "image": image,
                        "name": name,
                        "env": _sanitize_env(environment),
                        "ports": _sanitize_ports(ports),
                        "volumes": volumes,
                        "detach": detach,
                        "auto_remove": auto_remove,
                        "workdir": working_dir,
                        "user": user,
                        "stdin_open": stdin_open,
                        "tty": tty,
                    }
                ),
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
                ports=ports,
                volumes=volumes,
                detach=detach,
                auto_remove=auto_remove,
                working_dir=working_dir,
                user=user,
                stdin_open=stdin_open,
                tty=tty,
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

    def stop_container_result(self, container_id: str, timeout: int = 10) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.stop",
                args=redact_for_log({"id": container_id, "timeout": timeout}),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.stop",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            self.stop_container(container_id=container_id, timeout=timeout)
            return ToolResult.ok_result(
                stdout="ok",
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"id": container_id},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"id": container_id},
            )

    def exec_in_container_result(
        self,
        container_id: str,
        cmd: List[str] | str,
        *,
        workdir: Optional[str] = None,
        user: Optional[str] = None,
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.exec",
                args=redact_for_log(
                    {"id": container_id, "cmd": cmd, "cwd": workdir, "user": user}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.exec",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            rc, stdout, stderr = self.exec_in_container(
                container_id=container_id, cmd=cmd, workdir=workdir, user=user
            )
            meta = {
                "id": container_id,
                "cmd": cmd,
                "cwd": workdir,
                "user": user,
                "rc": rc,
            }
            if rc == 0:
                return ToolResult.ok_result(
                    stdout=stdout, exit_code=rc, latency_ms=_now_ms() - start, meta=meta
                )
            return ToolResult.err_result(
                error_type="Runtime",
                stderr=stderr or stdout,
                latency_ms=_now_ms() - start,
                meta=meta,
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"id": container_id, "cmd": cmd},
            )

    def copy_to_container_result(
        self, container_id: str, src_path: str | Path, dest_path: str | Path
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.cp_to",
                args=redact_for_log(
                    {"id": container_id, "src": str(src_path), "dest": str(dest_path)}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.cp_to",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            self.copy_to_container(
                container_id=container_id, src_path=src_path, dest_path=dest_path
            )
            return ToolResult.ok_result(
                stdout="ok",
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"id": container_id, "src": str(src_path), "dest": str(dest_path)},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"id": container_id, "src": str(src_path), "dest": str(dest_path)},
            )

    def copy_from_container_result(
        self, container_id: str, src_path: str | Path, dest_dir: str | Path
    ) -> ToolResult:
        start = _now_ms()
        if dry_run.enabled:
            preview = dry_run.preview_payload(
                tool="docker.cp_from",
                args=redact_for_log(
                    {"id": container_id, "src": str(src_path), "dest": str(dest_dir)}
                ),
            )
            return ToolResult.ok_result(
                stdout="[DRY-RUN] docker.cp_from",
                latency_ms=_now_ms() - start,
                meta={"preview": preview},
            )
        try:
            dest = self.copy_from_container(
                container_id=container_id, src_path=src_path, dest_dir=dest_dir
            )
            return ToolResult.ok_result(
                stdout=str(dest),
                exit_code=0,
                latency_ms=_now_ms() - start,
                meta={"id": container_id, "src": str(src_path), "dest": str(dest_dir)},
            )
        except Exception as e:
            return ToolResult.err_result(
                error_type=_errtype(e),
                stderr=str(e),
                latency_ms=_now_ms() - start,
                meta={"id": container_id, "src": str(src_path), "dest": str(dest_dir)},
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
