# aegis/tools/builtins.py
"""
Central adapters that expose executor methods as agent-callable tools.

Each adapter:
- is decorated with @tool(name, input_model, timeout)
- accepts keyword-only `input_data` (Pydantic model instance)
- instantiates an executor (defaults are fine; call sites can pass args via model)
- returns the executor's ToolResult-producing method

Add new tools here; registry auto-discovers them on first use.
"""

from __future__ import annotations

from typing import Any

from aegis.utils.tooling import tool

# ---- Schemas ----
from aegis.schemas.tool_inputs import (
    LocalExecInput,
    HttpRequestInput,
    DockerPullInput,
    DockerRunInput,
    DockerStopInput,
    DockerExecInput,
    DockerCopyToInput,
    DockerCopyFromInput,
    K8sListPodsInput,
    K8sPodLogsInput,
    K8sExecInput,
    K8sApplyManifestInput,
    K8sDeleteObjectInput,
    K8sCreateJobInput,
    RedisSetInput,
    RedisGetInput,
    RedisDelInput,
    ScapyPingInput,
    ScapyTCPScanInput,
    ScapyARPScanInput,
    ScapySniffInput,
    ScapySendInput,
    SlackSendMessageInput,
    GitlabListProjectsInput,
    GitlabCreateIssueInput,
    SSHExecInput,
    SCPUloadInput,
    SCPDownloadInput,
    SSHTestFileInput,
    SeleniumActionInput,
    SeleniumPageDetailsInput,
    SeleniumScreenshotInput,
    PwntoolsInteractRemoteInput,
    PwntoolsInteractProcessInput,
    PwntoolsAsmInput,
    PwntoolsCyclicInput,
    PwntoolsInspectELFInput,
)

# ---- Executors ----
from aegis.executors.local_exec import LocalExecutor
from aegis.executors.http_exec import HttpExecutor
from aegis.executors.docker_exec import DockerExecutor
from aegis.executors.k8s_exec import K8sExecutor
from aegis.executors.redis_exec import RedisExecutor
from aegis.executors.scapy_exec import ScapyExecutor
from aegis.executors.slack_exec import SlackExecutor
from aegis.executors.gitlab_exec import GitlabExecutor
from aegis.executors.ssh_exec import SSHExecutor
from aegis.executors.selenium_exec import SeleniumExecutor
from aegis.executors.pwntools_exec import PwntoolsExecutor

# ---- Manifest helpers ----
from aegis.utils.manifest_store import resolve_manifest_or_target


# ---- Local ----


@tool("local.exec", LocalExecInput, timeout=300)
def local_exec_adapter(*, input_data: LocalExecInput, **_: Any):
    ex = LocalExecutor()
    return ex.run_result(
        command=input_data.command, timeout=input_data.timeout, shell=input_data.shell
    )


# ---- HTTP ----


@tool("http.request", HttpRequestInput, timeout=180)
def http_request_adapter(*, input_data: HttpRequestInput, **_: Any):
    ex = HttpExecutor(
        base_url=input_data.base_url, default_timeout=input_data.timeout or 30
    )
    return ex.request_result(
        method=input_data.method,
        url=input_data.url,
        headers=input_data.headers,
        params=input_data.params,
        data=input_data.data,
        json_payload=input_data.json_payload,
        timeout=input_data.timeout,
    )


# ---- Docker ----


@tool("docker.pull", DockerPullInput, timeout=600)
def docker_pull_adapter(*, input_data: DockerPullInput, **_: Any):
    ex = DockerExecutor()
    return ex.pull_image_result(
        name=input_data.name, tag=input_data.tag, auth_config=input_data.auth
    )


@tool("docker.run", DockerRunInput, timeout=600)
def docker_run_adapter(*, input_data: DockerRunInput, **_: Any):
    ex = DockerExecutor()
    return ex.run_container_result(
        image=input_data.image,
        name=input_data.name,
        command=input_data.command,
        environment=input_data.environment,
        detach=True,
        auto_remove=input_data.auto_remove,
        network=input_data.network,
        volumes=input_data.volumes,
        ports=input_data.ports,
        user=input_data.user,
        working_dir=input_data.working_dir,
    )


@tool("docker.stop", DockerStopInput, timeout=120)
def docker_stop_adapter(*, input_data: DockerStopInput, **_: Any):
    ex = DockerExecutor()
    return ex.stop_container_result(
        container_id_or_name=input_data.container, timeout=input_data.timeout or 10
    )


@tool("docker.exec", DockerExecInput, timeout=600)
def docker_exec_adapter(*, input_data: DockerExecInput, **_: Any):
    ex = DockerExecutor()
    return ex.exec_in_container_result(
        container_id_or_name=input_data.container,
        cmd=input_data.cmd,
        timeout=input_data.timeout,
    )


@tool("docker.cp_to", DockerCopyToInput, timeout=600)
def docker_cp_to_adapter(*, input_data: DockerCopyToInput, **_: Any):
    ex = DockerExecutor()
    return ex.copy_to_container_result(
        container_id_or_name=input_data.container,
        src_path=input_data.src,
        dest_path=input_data.dest,
    )


@tool("docker.cp_from", DockerCopyFromInput, timeout=600)
def docker_cp_from_adapter(*, input_data: DockerCopyFromInput, **_: Any):
    ex = DockerExecutor()
    return ex.copy_from_container_result(
        container_id_or_name=input_data.container,
        src_path=input_data.src,
        dest_path=input_data.dest,
    )


# ---- Kubernetes ----


@tool("k8s.list_pods", K8sListPodsInput, timeout=120)
def k8s_list_pods_adapter(*, input_data: K8sListPodsInput, **_: Any):
    ex = K8sExecutor(
        kubeconfig_path=input_data.kubeconfig,
        context=input_data.context,
        in_cluster=input_data.in_cluster,
    )
    return ex.list_pods_result(
        namespace=input_data.namespace, label_selector=input_data.label_selector
    )


@tool("k8s.pod_logs", K8sPodLogsInput, timeout=180)
def k8s_pod_logs_adapter(*, input_data: K8sPodLogsInput, **_: Any):
    ex = K8sExecutor(
        kubeconfig_path=input_data.kubeconfig,
        context=input_data.context,
        in_cluster=input_data.in_cluster,
    )
    return ex.pod_logs_result(
        name=input_data.name,
        namespace=input_data.namespace,
        container=input_data.container,
        tail_lines=input_data.tail_lines,
    )


@tool("k8s.exec", K8sExecInput, timeout=300)
def k8s_exec_adapter(*, input_data: K8sExecInput, **_: Any):
    ex = K8sExecutor(
        kubeconfig_path=input_data.kubeconfig,
        context=input_data.context,
        in_cluster=input_data.in_cluster,
    )
    return ex.exec_in_pod_result(
        name=input_data.name,
        namespace=input_data.namespace,
        command=input_data.command,
        container=input_data.container,
        tty=input_data.tty,
    )


@tool("k8s.apply", K8sApplyManifestInput, timeout=300)
def k8s_apply_adapter(*, input_data: K8sApplyManifestInput, **_: Any):
    ex = K8sExecutor(
        kubeconfig_path=input_data.kubeconfig,
        context=input_data.context,
        in_cluster=input_data.in_cluster,
    )
    return ex.apply_manifest_result(manifest=input_data.manifest)


@tool("k8s.delete", K8sDeleteObjectInput, timeout=180)
def k8s_delete_adapter(*, input_data: K8sDeleteObjectInput, **_: Any):
    ex = K8sExecutor(
        kubeconfig_path=input_data.kubeconfig,
        context=input_data.context,
        in_cluster=input_data.in_cluster,
    )
    return ex.delete_object_result(
        kind=input_data.kind, name=input_data.name, namespace=input_data.namespace
    )


@tool("k8s.create_job", K8sCreateJobInput, timeout=300)
def k8s_create_job_adapter(*, input_data: K8sCreateJobInput, **_: Any):
    ex = K8sExecutor(
        kubeconfig_path=input_data.kubeconfig,
        context=input_data.context,
        in_cluster=input_data.in_cluster,
    )
    return ex.create_job_result(
        namespace=input_data.namespace,
        name=input_data.name,
        image=input_data.image,
        command=input_data.command,
        env=input_data.env,
        restart_policy=input_data.restart_policy,
    )


# ---- Redis ----


@tool("redis.set", RedisSetInput, timeout=60)
def redis_set_adapter(*, input_data: RedisSetInput, **_: Any):
    ex = RedisExecutor(
        host=input_data.host,
        port=input_data.port,
        db=input_data.db,
        password=input_data.password,
        socket_timeout=input_data.socket_timeout,
    )
    return ex.set_value_result(
        key=input_data.key, value=input_data.value, expire_s=input_data.expire_s
    )


@tool("redis.get", RedisGetInput, timeout=60)
def redis_get_adapter(*, input_data: RedisGetInput, **_: Any):
    ex = RedisExecutor(
        host=input_data.host,
        port=input_data.port,
        db=input_data.db,
        password=input_data.password,
        socket_timeout=input_data.socket_timeout,
    )
    return ex.get_value_result(key=input_data.key)


@tool("redis.del", RedisDelInput, timeout=60)
def redis_del_adapter(*, input_data: RedisDelInput, **_: Any):
    ex = RedisExecutor(
        host=input_data.host,
        port=input_data.port,
        db=input_data.db,
        password=input_data.password,
        socket_timeout=input_data.socket_timeout,
    )
    return ex.delete_value_result(key=input_data.key)


# ---- Scapy ----


@tool("scapy.ping", ScapyPingInput, timeout=120)
def scapy_ping_adapter(*, input_data: ScapyPingInput, **_: Any):
    ex = ScapyExecutor(require_root=input_data.require_root)
    return ex.ping_result(
        target_ip=input_data.target_ip,
        count=input_data.count,
        timeout_s=input_data.timeout_s,
    )


@tool("scapy.tcp_scan", ScapyTCPScanInput, timeout=300)
def scapy_tcp_scan_adapter(*, input_data: ScapyTCPScanInput, **_: Any):
    ex = ScapyExecutor(require_root=input_data.require_root)
    return ex.tcp_scan_result(
        target_ip=input_data.target_ip,
        ports=input_data.ports,
        timeout_s=input_data.timeout_s,
    )


@tool("scapy.arp_scan", ScapyARPScanInput, timeout=180)
def scapy_arp_scan_adapter(*, input_data: ScapyARPScanInput, **_: Any):
    ex = ScapyExecutor(require_root=input_data.require_root)
    return ex.arp_scan_result(
        network_cidr=input_data.network_cidr, timeout_s=input_data.timeout_s
    )


@tool("scapy.sniff", ScapySniffInput, timeout=300)
def scapy_sniff_adapter(*, input_data: ScapySniffInput, **_: Any):
    ex = ScapyExecutor(require_root=input_data.require_root)
    return ex.sniff_packets_result(
        iface=input_data.iface,
        count=input_data.count,
        timeout_s=input_data.timeout_s,
        bpf_filter=input_data.bpf_filter,
    )


@tool("scapy.send", ScapySendInput, timeout=120)
def scapy_send_adapter(*, input_data: ScapySendInput, **_: Any):
    ex = ScapyExecutor(require_root=input_data.require_root)
    return ex.craft_and_send_packet_result(
        dst_ip=input_data.dst_ip,
        dst_port=input_data.dst_port,
        payload=input_data.payload,
        protocol=input_data.protocol,
    )


# ---- Slack ----


@tool("slack.send_message", SlackSendMessageInput, timeout=60)
def slack_send_adapter(*, input_data: SlackSendMessageInput, **_: Any):
    ex = SlackExecutor(bot_token=input_data.bot_token)
    return ex.send_message_result(
        channel=input_data.channel, text=input_data.text, thread_ts=input_data.thread_ts
    )


# ---- GitLab ----


@tool("gitlab.list_projects", GitlabListProjectsInput, timeout=120)
def gitlab_list_projects_adapter(*, input_data: GitlabListProjectsInput, **_: Any):
    ex = GitlabExecutor()
    return ex.list_projects_result(
        search=input_data.search, visibility=input_data.visibility
    )


@tool("gitlab.create_issue", GitlabCreateIssueInput, timeout=120)
def gitlab_create_issue_adapter(*, input_data: GitlabCreateIssueInput, **_: Any):
    ex = GitlabExecutor()
    return ex.create_issue_result(
        project_id=input_data.project_id,
        title=input_data.title,
        description=input_data.description,
        labels=input_data.labels,
    )


# ---- SSH / SCP (manifest-aware, multi-NIC) ----


def _make_ssh_executor(
    input_data: SSHExecInput | SCPUloadInput | SCPDownloadInput | SSHTestFileInput,
) -> SSHExecutor:
    manifest, target = resolve_manifest_or_target(
        machine_id=getattr(input_data, "machine_id", None),
        manifest_dir=getattr(input_data, "manifest_dir", None),
        manifest_inline=getattr(input_data, "manifest", None),
        ssh_target=getattr(input_data, "ssh_target", None),
    )
    ex = SSHExecutor(
        manifest=manifest,
        ssh_target=target,
        username=input_data.username,
        port=None,
        private_key_path=input_data.key_path,
        password=input_data.password,
        timeout=input_data.timeout or 120,
        interface_name=input_data.interface_name,
    )
    return ex


@tool("ssh.exec", SSHExecInput, timeout=600)
def ssh_exec_adapter(*, input_data: SSHExecInput, **_: Any):
    ex = _make_ssh_executor(input_data)
    return ex.run_result(command=input_data.command, timeout=input_data.timeout)


@tool("scp.upload", SCPUloadInput, timeout=600)
def scp_upload_adapter(*, input_data: SCPUloadInput, **_: Any):
    ex = _make_ssh_executor(input_data)
    return ex.upload_result(
        local_path=input_data.local_path,
        remote_path=input_data.remote_path,
        timeout=input_data.timeout,
    )


@tool("scp.download", SCPDownloadInput, timeout=600)
def scp_download_adapter(*, input_data: SCPDownloadInput, **_: Any):
    ex = _make_ssh_executor(input_data)
    return ex.download_result(
        remote_path=input_data.remote_path,
        local_path=input_data.local_path,
        timeout=input_data.timeout,
    )


@tool("ssh.test_file", SSHTestFileInput, timeout=180)
def ssh_test_file_adapter(*, input_data: SSHTestFileInput, **_: Any):
    ex = _make_ssh_executor(input_data)
    return ex.check_file_exists_result(
        file_path=input_data.path, timeout=input_data.timeout
    )


# ---- Selenium ----


@tool("selenium.action", SeleniumActionInput, timeout=300)
def selenium_action_adapter(*, input_data: SeleniumActionInput, **_: Any):
    ex = SeleniumExecutor(
        headless=input_data.headless,
        driver_path=input_data.driver_path,
        implicit_wait_s=input_data.implicit_wait_s,
    )
    return ex.execute_action_result(
        action=input_data.action,
        url=input_data.url,
        selector=input_data.selector,
        text=input_data.text,
        screenshot_path=input_data.screenshot_path,
    )


@tool("selenium.page_details", SeleniumPageDetailsInput, timeout=180)
def selenium_page_details_adapter(*, input_data: SeleniumPageDetailsInput, **_: Any):
    ex = SeleniumExecutor(
        headless=input_data.headless,
        driver_path=input_data.driver_path,
        implicit_wait_s=input_data.implicit_wait_s,
    )
    return ex.get_page_details_result(url=input_data.url, selector=input_data.selector)


@tool("selenium.screenshot", SeleniumScreenshotInput, timeout=180)
def selenium_screenshot_adapter(*, input_data: SeleniumScreenshotInput, **_: Any):
    ex = SeleniumExecutor(
        headless=input_data.headless,
        driver_path=input_data.driver_path,
        implicit_wait_s=input_data.implicit_wait_s,
    )
    return ex.take_screenshot_result(url=input_data.url, path=input_data.path)


# ---- Pwntools ----


@tool("pwntools.interact_remote", PwntoolsInteractRemoteInput, timeout=600)
def pwntools_interact_remote_adapter(
    *, input_data: PwntoolsInteractRemoteInput, **_: Any
):
    ex = PwntoolsExecutor(arch=input_data.arch, os_name=input_data.os_name)
    return ex.interact_remote_result(
        host=input_data.host,
        port=input_data.port,
        send_lines=input_data.send_lines,
        recv_until=input_data.recv_until,
        timeout_s=input_data.timeout_s,
    )


@tool("pwntools.interact_process", PwntoolsInteractProcessInput, timeout=600)
def pwntools_interact_process_adapter(
    *, input_data: PwntoolsInteractProcessInput, **_: Any
):
    ex = PwntoolsExecutor(arch=input_data.arch, os_name=input_data.os_name)
    return ex.interact_process_result(
        binary_path=input_data.binary_path,
        argv=input_data.argv,
        send_lines=input_data.send_lines,
        recv_until=input_data.recv_until,
        timeout_s=input_data.timeout_s,
    )


@tool("pwntools.asm", PwntoolsAsmInput, timeout=120)
def pwntools_asm_adapter(*, input_data: PwntoolsAsmInput, **_: Any):
    ex = PwntoolsExecutor(arch=input_data.arch, os_name="linux")
    return ex.craft_shellcode_result(
        arch=input_data.arch, instructions=input_data.instructions
    )


@tool("pwntools.cyclic", PwntoolsCyclicInput, timeout=60)
def pwntools_cyclic_adapter(*, input_data: PwntoolsCyclicInput, **_: Any):
    ex = PwntoolsExecutor()
    return ex.generate_cyclic_pattern_result(length=input_data.length)


@tool("pwntools.inspect_elf", PwntoolsInspectELFInput, timeout=120)
def pwntools_inspect_elf_adapter(*, input_data: PwntoolsInspectELFInput, **_: Any):
    ex = PwntoolsExecutor()
    return ex.inspect_elf_result(path=input_data.path)
