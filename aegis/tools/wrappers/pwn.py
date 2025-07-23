# aegis/tools/wrappers/pwn.py
"""
Wrapper tools for leveraging the 'pwntools' library for advanced
network interaction, binary analysis, and security testing.

These tools provide a safe and structured interface to some of the most
powerful features of pwntools, enabling the agent to perform tasks related
to exploit development and security challenges.
"""
from typing import Optional

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.pwntools_exec import PWNTOOLS_AVAILABLE_FOR_EXECUTOR, PwntoolsExecutor
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class PwnRemoteConnectInput(BaseModel):
    host: str = Field(..., description="The hostname or IP address of the target.")
    port: int = Field(
        ..., gt=0, lt=65536, description="The port number of the target service."
    )
    payload: Optional[str] = Field(
        None, description="Optional initial payload to send upon connection."
    )
    timeout: int = Field(
        5, description="Timeout in seconds for the connection and receive operations."
    )


class PwnShellcodeCraftInput(BaseModel):
    arch: str = Field(
        "amd64", description="The target architecture (e.g., 'amd64', 'i386', 'arm')."
    )
    os: str = Field(
        "linux", description="The target operating system (usually 'linux')."
    )
    command: str = Field(
        "sh",
        description="The command for the shellcode to execute (e.g., 'sh', 'cat /etc/passwd').",
    )


class PwnCyclicPatternInput(BaseModel):
    length: int = Field(
        100, description="The length of the cyclic pattern to generate."
    )
    find: Optional[str] = Field(
        None,
        description="A 4-byte value (e.g., '0x61616162' or 'aaba') to find the offset of.",
    )


class PwnElfInspectorInput(BaseModel):
    file_path: str = Field(
        ..., description="The local path to the ELF binary to inspect."
    )


class PwnProcessInteractionInput(BaseModel):
    file_path: str = Field(..., description="The local path to the executable to run.")
    payload: str = Field(
        ..., description="The payload to send to the process's standard input."
    )
    timeout: int = Field(5, description="Timeout in seconds for the interaction.")


# === Tools ===


@register_tool(
    name="pwn_remote_connect",
    input_model=PwnRemoteConnectInput,
    description="Connects to a remote TCP service, sends an optional payload, and receives data. Uses PwntoolsExecutor",
    tags=["pwn", "network", "exploit", "security", "wrapper"],
    category="security",
    safe_mode=False,
)
def pwn_remote_connect(input_data: PwnRemoteConnectInput) -> str:
    """Uses PwntoolsExecutor to establish a raw TCP connection, send data, and receive a response."""
    if not PWNTOOLS_AVAILABLE_FOR_EXECUTOR:
        raise ToolExecutionError("The 'pwntools' library is not installed.")

    logger.info(f"Tool 'pwn_remote_connect' to {input_data.host}:{input_data.port}")
    executor = PwntoolsExecutor(default_timeout=input_data.timeout)

    def _interaction(conn):
        if input_data.payload:
            conn.sendline(input_data.payload.encode("utf-8"))
        return conn.recvall().decode("utf-8", errors="ignore")

    return executor.interact_remote(
        input_data.host, input_data.port, _interaction, timeout=input_data.timeout
    )


@register_tool(
    name="pwn_shellcode_craft",
    input_model=PwnShellcodeCraftInput,
    description="Generates common shellcode for a specified architecture and command.",
    tags=["pwn", "exploit", "shellcode", "security"],
    category="security",
    safe_mode=False,
)
def pwn_shellcode_craft(input_data: PwnShellcodeCraftInput) -> str:
    """Uses the PwntoolsExecutor to generate shellcode assembly."""
    if not PWNTOOLS_AVAILABLE_FOR_EXECUTOR:
        raise ToolExecutionError("The 'pwntools' library is not installed.")

    logger.info(
        f"Crafting shellcode for arch='{input_data.arch}' os='{input_data.os}' cmd='{input_data.command}'"
    )
    executor = PwntoolsExecutor()
    return executor.craft_shellcode(input_data.arch, input_data.os, input_data.command)


@register_tool(
    name="pwn_cyclic_pattern",
    input_model=PwnCyclicPatternInput,
    description="Generates a De Bruijn pattern or finds an offset within one.",
    tags=["pwn", "exploit", "buffer-overflow", "security"],
    category="security",
    safe_mode=True,
)
def pwn_cyclic_pattern(input_data: PwnCyclicPatternInput) -> str:
    """Uses the PwntoolsExecutor to generate or find a cyclic pattern."""
    if not PWNTOOLS_AVAILABLE_FOR_EXECUTOR:
        raise ToolExecutionError("The 'pwntools' library is not installed.")

    logger.info(
        f"Generating cyclic pattern with length {input_data.length} or finding '{input_data.find}'"
    )
    executor = PwntoolsExecutor()
    return executor.generate_cyclic_pattern(input_data.length, input_data.find)


@register_tool(
    name="pwn_elf_inspector",
    input_model=PwnElfInspectorInput,
    description="Inspects an ELF binary to check for security mitigations and other properties.",
    tags=["pwn", "binary-analysis", "elf", "security"],
    category="security",
    safe_mode=True,
)
def pwn_elf_inspector(input_data: PwnElfInspectorInput) -> str:
    """Uses the PwntoolsExecutor to perform static analysis on a binary."""
    if not PWNTOOLS_AVAILABLE_FOR_EXECUTOR:
        raise ToolExecutionError("The 'pwntools' library is not installed.")

    logger.info(f"Inspecting ELF binary: {input_data.file_path}")
    executor = PwntoolsExecutor()
    return executor.inspect_elf(input_data.file_path)


@register_tool(
    name="pwn_process_interaction",
    input_model=PwnProcessInteractionInput,
    description="Starts a local process and interacts with it by sending a payload. Uses PwntoolsExecutor.",
    tags=["pwn", "binary-analysis", "local", "security"],
    category="security",
    safe_mode=False,
)
def pwn_process_interaction(input_data: PwnProcessInteractionInput) -> str:
    """Starts a local process, sends it a payload, and returns the output using PwntoolsExecutor."""
    if not PWNTOOLS_AVAILABLE_FOR_EXECUTOR:
        raise ToolExecutionError("The 'pwntools' library is not installed.")

    logger.info(f"Tool 'pwn_process_interaction' for file: {input_data.file_path}")
    executor = PwntoolsExecutor(default_timeout=input_data.timeout)

    def _interaction(proc):
        proc.sendline(input_data.payload.encode("utf-8"))
        return proc.recvall(timeout=input_data.timeout).decode("utf-8", errors="ignore")

    return executor.interact_process(
        input_data.file_path, _interaction, timeout=input_data.timeout
    )
