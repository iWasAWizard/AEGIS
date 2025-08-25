# aegis/schemas/tool_inputs.py
"""
Pydantic input models for tool registry entries.

These are purposefully minimal and aligned with the executor adapters in aegis/tools/builtins.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---- Local ----


class LocalExecInput(BaseModel):
    command: str = Field(..., description="Shell command to execute")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    shell: bool = Field(False, description="Run via system shell")


# ---- HTTP ----


class HttpRequestInput(BaseModel):
    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Absolute or relative URL")
    base_url: Optional[str] = Field(None, description="Optional base URL")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers")
    params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")
    data: Optional[Any] = Field(None, description="Raw request body")
    json_payload: Optional[Dict[str, Any]] = Field(None, description="JSON payload")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")


# ---- Docker ----


class DockerPullInput(BaseModel):
    name: str = Field(..., description="Repository name")
    tag: str = Field("latest", description="Image tag")
    auth: Optional[Dict[str, Any]] = Field(None, description="Registry auth config")


class DockerRunInput(BaseModel):
    image: str
    name: Optional[str] = None
    command: Optional[List[str] | str] = None
    environment: Optional[Dict[str, str] | List[str]] = None
    auto_remove: bool = False
    network: Optional[str] = None
    volumes: Optional[Dict[str, Dict[str, str]]] = None
    ports: Optional[Dict[str, int | str]] = None
    user: Optional[str] = None
    working_dir: Optional[str] = None


class DockerStopInput(BaseModel):
    container: str
    timeout: Optional[int] = 10


class DockerExecInput(BaseModel):
    container: str
    cmd: List[str] | str
    timeout: Optional[int] = None


class DockerCopyToInput(BaseModel):
    container: str
    src: str
    dest: str


class DockerCopyFromInput(BaseModel):
    container: str
    src: str
    dest: str


# ---- Kubernetes ----


class _ClusterBase(BaseModel):
    kubeconfig: Optional[str] = Field(None, description="Path to kubeconfig")
    context: Optional[str] = Field(None, description="Context name in kubeconfig")
    in_cluster: bool = Field(False, description="Use in-cluster auth")


class KubernetesListPodsInput(_ClusterBase):
    namespace: str = "default"
    label_selector: Optional[str] = None


class KubernetesPodLogsInput(_ClusterBase):
    name: str
    namespace: str = "default"
    container: Optional[str] = None
    tail_lines: Optional[int] = None


class KubernetesExecInput(_ClusterBase):
    name: str
    namespace: str
    command: List[str]
    container: Optional[str] = None
    tty: bool = False


class KubernetesApplyManifestInput(_ClusterBase):
    manifest: Dict[str, Any]


class KubernetesDeleteObjectInput(_ClusterBase):
    kind: str
    name: str
    namespace: str = "default"


class KubernetesCreateJobInput(_ClusterBase):
    namespace: str
    name: str
    image: str
    command: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    restart_policy: str = "Never"


# ---- Redis ----


class _RedisBase(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: int = 5


class RedisSetInput(_RedisBase):
    key: str
    value: str
    expire_s: Optional[int] = None


class RedisGetInput(_RedisBase):
    key: str


class RedisDelInput(_RedisBase):
    key: str


# ---- Scapy ----


class _ScapyBase(BaseModel):
    require_root: bool = False


class ScapyPingInput(_ScapyBase):
    target_ip: str
    count: int = 1
    timeout_s: int = 2


class ScapyTCPScanInput(_ScapyBase):
    target_ip: str
    ports: List[int]
    timeout_s: int = 2


class ScapyARPScanInput(_ScapyBase):
    network_cidr: str
    timeout_s: int = 2


class ScapySniffInput(_ScapyBase):
    iface: Optional[str] = None
    count: int = 10
    timeout_s: int = 5
    bpf_filter: Optional[str] = None


class ScapySendInput(_ScapyBase):
    dst_ip: str
    dst_port: Optional[int] = None
    payload: Optional[bytes | str] = None
    protocol: str = "ICMP"


# ---- Slack ----


class SlackSendMessageInput(BaseModel):
    channel: str
    text: str
    thread_ts: Optional[str] = None
    bot_token: Optional[str] = Field(
        None, description="Optional override; else settings is used"
    )


# ---- GitLab ----


class GitlabListProjectsInput(BaseModel):
    search: Optional[str] = None
    visibility: Optional[str] = Field(None, description="public|internal|private")


class GitlabCreateIssueInput(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    labels: Optional[List[str]] = None


# ---- SSH / SCP ----


class _SSHBase(BaseModel):
    machine_id: Optional[str] = Field(
        None, description="ID of the machine in your manifest store"
    )
    interface_name: Optional[str] = Field(
        None, description="Which NIC to use (e.g., 'mgmt0'). Defaults to primary."
    )
    username: str = Field("root", description="SSH username")
    key_path: Optional[str] = Field(
        None, description="Path to private key file for key-based auth"
    )
    password: Optional[str] = Field(
        None, description="Password for password-based auth (avoid if possible)"
    )
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    manifest_dir: Optional[str] = Field(
        None, description="Directory containing <machine_id>.json|yaml manifest files"
    )
    manifest: Optional[Dict[str, Any]] = Field(
        None, description="Inline manifest object (MachineManifest-like dict)"
    )
    ssh_target: Optional[str] = Field(
        None, description="Direct host/ip override (used if no manifest provided)"
    )


class SSHExecInput(_SSHBase):
    command: str = Field(..., description="Command to run remotely")


class SCPUloadInput(_SSHBase):
    local_path: str = Field(..., description="Source file on local filesystem")
    remote_path: str = Field(..., description="Destination path on remote host")


class SCPDownloadInput(_SSHBase):
    remote_path: str = Field(..., description="Source file on remote host")
    local_path: str = Field(..., description="Destination path on local filesystem")


class SSHTestFileInput(_SSHBase):
    path: str = Field(..., description="Remote file path to test existence")


# ---- Selenium ----


class SeleniumActionInput(BaseModel):
    action: str = Field(..., description="goto|click|type|screenshot")
    url: str = Field(..., description="Target URL")
    selector: Optional[str] = Field(None, description="CSS selector (for click/type)")
    text: Optional[str] = Field(None, description="Text to type (for action=type)")
    screenshot_path: Optional[str] = Field(
        None, description="Path for screenshot (action=screenshot)"
    )
    headless: bool = Field(True, description="Run Chrome headless")
    driver_path: Optional[str] = Field(None, description="Chromedriver path override")
    implicit_wait_s: int = Field(5, description="Implicit wait seconds")


class SeleniumPageDetailsInput(BaseModel):
    url: str = Field(..., description="Target URL")
    selector: Optional[str] = Field(None, description="CSS selector to extract text")
    headless: bool = Field(True, description="Run Chrome headless")
    driver_path: Optional[str] = Field(None, description="Chromedriver path override")
    implicit_wait_s: int = Field(5, description="Implicit wait seconds")


class SeleniumScreenshotInput(BaseModel):
    url: str = Field(..., description="Target URL")
    path: str = Field(..., description="Destination path for screenshot")
    headless: bool = Field(True, description="Run Chrome headless")
    driver_path: Optional[str] = Field(None, description="Chromedriver path override")
    implicit_wait_s: int = Field(5, description="Implicit wait seconds")


# ---- Pwntools ----


class PwntoolsInteractRemoteInput(BaseModel):
    host: str
    port: int
    send_lines: Optional[List[str]] = None
    recv_until: Optional[str] = None
    timeout_s: int = 5
    arch: str = "amd64"
    os_name: str = "linux"


class PwntoolsInteractProcessInput(BaseModel):
    binary_path: str
    argv: Optional[List[str]] = None
    send_lines: Optional[List[str]] = None
    recv_until: Optional[str] = None
    timeout_s: int = 5
    arch: str = "amd64"
    os_name: str = "linux"


class PwntoolsAsmInput(BaseModel):
    arch: str
    instructions: List[str]


class PwntoolsCyclicInput(BaseModel):
    length: int


class PwntoolsInspectELFInput(BaseModel):
    path: str
