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

# Import PwntoolsExecutor
from aegis.executors.pwntools import PwntoolsExecutor
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

# pwntools import for non-executor tools
try:
    from pwn import shellcraft, context, cyclic, cyclic_find, ELF  # type: ignore

    # PwnlibException already imported by executor, but good for clarity if needed elsewhere
    from pwnlib.exception import PwnlibException  # type: ignore

    PWNTOOLS_AVAILABLE = True
except ImportError:
    PWNTOOLS_AVAILABLE = False

    # Define dummy types for non-executor tools if pwntools is not available for type hinting
    class ShellCraft:
        pass  # type: ignore

    class Context:
        pass  # type: ignore

    def cyclic(n, length=None):
        return b""  # type: ignore

    def cyclic_find(subsequence, n=None):
        return -1  # type: ignore

    class ELF:
        pass  # type: ignore

    class PwnlibException(Exception):
        pass  # type: ignore


logger = setup_logger(__name__)


# === Input Models === (Remain the same)


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
    """Uses PwntoolsExecutor to establish a raw TCP connection, send data, and receive a response.

    :param input_data: An object containing host, port, payload, and timeout.
    :type input_data: PwnRemoteConnectInput
    :return: The decoded response from the remote service.
    :rtype: str
    :raises ToolExecutionError: If `pwntools` is not installed or connection/interaction fails.
    """
    if (
        not PWNTOOLS_AVAILABLE
    ):  # Redundant if executor also checks, but good for early tool-level fail
        raise ToolExecutionError(
            "The 'pwntools' library is not installed. This tool cannot be used."
        )

    logger.info(f"Tool 'pwn_remote_connect' to {input_data.host}:{input_data.port}")
    executor = PwntoolsExecutor(default_timeout=input_data.timeout)

    def _interaction(conn):  # conn is a pwntools tube
        if input_data.payload:
            conn.sendline(input_data.payload.encode("utf-8"))
        response_bytes = conn.recvall()  # Uses tube's timeout
        return response_bytes.decode("utf-8", errors="ignore")

    try:
        return executor.interact_remote(
            input_data.host, input_data.port, _interaction, timeout=input_data.timeout
        )
    except ToolExecutionError:  # Propagate from executor
        raise
    except (
        Exception
    ) as e:  # Catch any other unexpected error within this tool's direct logic
        logger.exception(
            f"Unexpected error in pwn_remote_connect tool logic for {input_data.host}:{input_data.port}"
        )
        raise ToolExecutionError(f"Unexpected tool error in pwn_remote_connect: {e}")


@register_tool(
    name="pwn_shellcode_craft",
    input_model=PwnShellcodeCraftInput,
    description="Generates common shellcode for a specified architecture and command.",
    tags=["pwn", "exploit", "shellcode", "security"],
    category="security",
    safe_mode=False,
)
def pwn_shellcode_craft(input_data: PwnShellcodeCraftInput) -> str:
    """Generates shellcode using pwntools' shellcraft module and returns it as assembly.

    :param input_data: An object specifying the architecture, OS, and command.
    :type input_data: PwnShellcodeCraftInput
    :return: A string containing the generated shellcode assembly.
    :rtype: str
    :raises ToolExecutionError: If `pwntools` is not installed or generation fails.
    """
    if not PWNTOOLS_AVAILABLE:
        raise ToolExecutionError(
            "The 'pwntools' library is not installed. This tool cannot be used."
        )
    logger.info(
        f"Crafting shellcode for arch='{input_data.arch}' os='{input_data.os}' cmd='{input_data.command}'"
    )
    try:
        context.clear()
        context.arch = input_data.arch
        context.os = input_data.os

        if input_data.command == "sh":
            shellcode_asm = shellcraft.sh()
        elif input_data.command.startswith("cat"):
            filename = input_data.command.split(None, 1)[1]
            shellcode_asm = shellcraft.cat(filename)
        else:
            raise ToolExecutionError(
                "Unsupported shellcode command. Supported: 'sh', 'cat <file>'."
            )

        return shellcode_asm
    except Exception as e:
        logger.error(f"Shellcode generation failed: {e}")
        raise ToolExecutionError(f"Shellcode generation failed: {e}")


@register_tool(
    name="pwn_cyclic_pattern",
    input_model=PwnCyclicPatternInput,
    description="Generates a De Bruijn pattern or finds an offset within one.",
    tags=["pwn", "exploit", "buffer-overflow", "security"],
    category="security",
    safe_mode=True,
)
def pwn_cyclic_pattern(input_data: PwnCyclicPatternInput) -> str:
    """Generates a cyclic pattern or finds the offset of a substring within it.

    This is a common tool used in buffer overflow exploit development to find the
    exact offset required to overwrite a return address.

    :param input_data: An object for generating a pattern or finding an offset.
    :type input_data: PwnCyclicPatternInput
    :return: The generated pattern or the found offset.
    :rtype: str
    :raises ToolExecutionError: If `pwntools` is not installed or pattern operation fails.
    """
    if not PWNTOOLS_AVAILABLE:
        raise ToolExecutionError(
            "The 'pwntools' library is not installed. This tool cannot be used."
        )

    try:
        if input_data.find:
            value_to_find = input_data.find
            if value_to_find.startswith("0x"):
                value_to_find = int(value_to_find, 16)
            else:
                value_to_find = value_to_find.encode("utf-8")

            offset = cyclic_find(value_to_find, n=4)
            logger.info(f"Found cyclic offset for '{input_data.find}': {offset}")
            return f"Offset for '{input_data.find}' is: {offset}"
        else:
            pattern_bytes = cyclic(input_data.length, n=4)
            pattern = pattern_bytes.decode("utf-8", errors="ignore")
            logger.info(f"Generated {input_data.length}-byte cyclic pattern.")
            return f"Generated pattern: {pattern}"
    except Exception as e:
        logger.error(f"Cyclic pattern operation failed: {e}")
        raise ToolExecutionError(f"Cyclic pattern operation failed: {e}")


@register_tool(
    name="pwn_elf_inspector",
    input_model=PwnElfInspectorInput,
    description="Inspects an ELF binary to check for security mitigations and other properties.",
    tags=["pwn", "binary-analysis", "elf", "security"],
    category="security",
    safe_mode=True,
)
def pwn_elf_inspector(input_data: PwnElfInspectorInput) -> str:
    """Uses pwntools' ELF functionality to perform static analysis on a binary.

    :param input_data: An object containing the path to the ELF file.
    :type input_data: PwnElfInspectorInput
    :return: A formatted string of the binary's properties.
    :rtype: str
    :raises ToolExecutionError: If `pwntools` is not installed or ELF inspection fails.
    """
    if not PWNTOOLS_AVAILABLE:
        raise ToolExecutionError(
            "The 'pwntools' library is not installed. This tool cannot be used."
        )
    logger.info(f"Inspecting ELF binary: {input_data.file_path}")
    try:
        elf = ELF(input_data.file_path)
        results = [
            f"File: {elf.path}",
            f"Arch: {elf.arch}",
            f"Bits: {elf.bits}",
            f"OS: {elf.os}",
            f"RELRO: {elf.relro}",
            f"PIE: {elf.pie}",
            f"NX: {elf.nx}",
            f"Canary: {elf.canary}",
            f"Functions (first 10): {list(elf.functions.keys())[:10]}",
        ]
        return "\n".join(results)
    except FileNotFoundError:
        logger.error(f"ELF file not found: '{input_data.file_path}'")
        raise ToolExecutionError(f"ELF file not found: {input_data.file_path}")
    except Exception as e:
        logger.error(f"Failed to inspect ELF file '{input_data.file_path}': {e}")
        raise ToolExecutionError(f"Failed to inspect ELF '{input_data.file_path}': {e}")


@register_tool(
    name="pwn_process_interaction",
    input_model=PwnProcessInteractionInput,
    description="Starts a local process and interacts with it by sending a payload. Uses PwntoolsExecutor.",
    tags=["pwn", "binary-analysis", "local", "security"],
    category="security",
    safe_mode=False,
)
def pwn_process_interaction(input_data: PwnProcessInteractionInput) -> str:
    """Starts a local process, sends it a payload, and returns the output using PwntoolsExecutor.

    :param input_data: An object specifying the executable path and payload.
    :type input_data: PwnProcessInteractionInput
    :return: The decoded output from the process.
    :rtype: str
    :raises ToolExecutionError: If `pwntools` is not installed or process interaction fails.
    """
    if not PWNTOOLS_AVAILABLE:
        raise ToolExecutionError(
            "The 'pwntools' library is not installed. This tool cannot be used."
        )

    logger.info(f"Tool 'pwn_process_interaction' for file: {input_data.file_path}")
    executor = PwntoolsExecutor(default_timeout=input_data.timeout)

    def _interaction(proc):  # proc is a pwntools tube
        proc.sendline(input_data.payload.encode("utf-8"))
        response = proc.recvall(timeout=input_data.timeout).decode(
            "utf-8", errors="ignore"
        )  # Use input_data.timeout for recvall
        return response

    try:
        return executor.interact_process(
            input_data.file_path, _interaction, timeout=input_data.timeout
        )
    except ToolExecutionError:  # Propagate from executor
        raise
    except (
        Exception
    ) as e:  # Catch any other unexpected error within this tool's direct logic
        logger.exception(
            f"Unexpected error in pwn_process_interaction tool logic for {input_data.file_path}"
        )
        raise ToolExecutionError(
            f"Unexpected tool error in pwn_process_interaction: {e}"
        )
