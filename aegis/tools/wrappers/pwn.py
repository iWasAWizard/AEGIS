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
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

# Attempt to import pwntools, but don't fail if it's not installed.
# Each tool will check for its availability at runtime.
try:
    from pwn import remote, process, shellcraft, context, cyclic, cyclic_find, ELF  # type: ignore
    from pwnlib.exception import PwnlibException  # type: ignore

    PWNTOOLS_AVAILABLE = True
except ImportError:
    PWNTOOLS_AVAILABLE = False

logger = setup_logger(__name__)


# === Input Models ===


class PwnRemoteConnectInput(BaseModel):
    """Input model for connecting to a remote TCP service with pwntools.

    :ivar host: The hostname or IP address of the target.
    :vartype host: str
    :ivar port: The port number of the target service.
    :vartype port: int
    :ivar payload: Optional initial payload to send upon connection.
    :vartype payload: Optional[str]
    :ivar timeout: Timeout in seconds for the connection and receive operations.
    :vartype timeout: int
    """

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
    """Input model for generating shellcode.

    :ivar arch: The target architecture (e.g., 'amd64', 'i386', 'arm').
    :vartype arch: str
    :ivar os: The target operating system (usually 'linux').
    :vartype os: str
    :ivar command: The command for the shellcode to execute (e.g., 'sh', 'cat /etc/passwd').
    :vartype command: str
    """

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
    """Input for generating or finding an offset in a De Bruijn pattern.

    :ivar length: The length of the cyclic pattern to generate.
    :vartype length: int
    :ivar find: A 4-byte value (e.g., '0x61616162' or 'aaba') to find the offset of.
    :vartype find: Optional[str]
    """

    length: int = Field(
        100, description="The length of the cyclic pattern to generate."
    )
    find: Optional[str] = Field(
        None,
        description="A 4-byte value (e.g., '0x61616162' or 'aaba') to find the offset of.",
    )


class PwnElfInspectorInput(BaseModel):
    """Input for inspecting a local ELF binary.

    :ivar file_path: The local path to the ELF binary to inspect.
    :vartype file_path: str
    """

    file_path: str = Field(
        ..., description="The local path to the ELF binary to inspect."
    )


class PwnProcessInteractionInput(BaseModel):
    """Input for interacting with a local process.

    :ivar file_path: The local path to the executable to run.
    :vartype file_path: str
    :ivar payload: The payload to send to the process's standard input.
    :vartype payload: str
    :ivar timeout: Timeout in seconds for the interaction.
    :vartype timeout: int
    """

    file_path: str = Field(..., description="The local path to the executable to run.")
    payload: str = Field(
        ..., description="The payload to send to the process's standard input."
    )
    timeout: int = Field(5, description="Timeout in seconds for the interaction.")


# === Tools ===


@register_tool(
    name="pwn_remote_connect",
    input_model=PwnRemoteConnectInput,
    description="Connects to a remote TCP service, sends an optional payload, and receives data. Requires pwntools.",
    tags=["pwn", "network", "exploit", "security", "wrapper"],
    category="security",
    safe_mode=False,
)
def pwn_remote_connect(input_data: PwnRemoteConnectInput) -> str:
    """Uses pwntools to establish a raw TCP connection, send data, and receive a response.

    :param input_data: An object containing host, port, payload, and timeout.
    :type input_data: PwnRemoteConnectInput
    :return: The decoded response from the remote service.
    :rtype: str
    :raises ToolExecutionError: If `pwntools` is not installed or a PwnlibException occurs.
    """
    if not PWNTOOLS_AVAILABLE:
        raise ToolExecutionError(
            "The 'pwntools' library is not installed. This tool cannot be used."
        )
    logger.info(
        f"Attempting pwntools connection to {input_data.host}:{input_data.port}"
    )
    conn = None
    try:
        conn = remote(input_data.host, input_data.port, timeout=input_data.timeout)
        if input_data.payload:
            conn.sendline(input_data.payload.encode("utf-8"))
        response_bytes = conn.recvall()
        return response_bytes.decode("utf-8", errors="ignore")
    except PwnlibException as e:  # type: ignore
        logger.error(
            f"pwntools connection to {input_data.host}:{input_data.port} failed: {e}"
        )
        raise ToolExecutionError(f"pwntools operation failed: {e}")
    except Exception as e:  # Catch other unexpected errors
        logger.exception(
            f"Unexpected error in pwn_remote_connect to {input_data.host}:{input_data.port}: {e}"
        )
        raise ToolExecutionError(f"Unexpected error in pwn_remote_connect: {e}")
    finally:
        if conn:
            conn.close()


@register_tool(
    name="pwn_shellcode_craft",
    input_model=PwnShellcodeCraftInput,
    description="Generates common shellcode for a specified architecture and command.",
    tags=["pwn", "exploit", "shellcode", "security"],
    category="security",
    safe_mode=False,  # Shellcode generation itself is safe, but its use is not.
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
        context.clear()  # type: ignore
        context.arch = input_data.arch  # type: ignore
        context.os = input_data.os  # type: ignore

        if input_data.command == "sh":
            shellcode_asm = shellcraft.sh()  # type: ignore
        elif input_data.command.startswith("cat"):
            filename = input_data.command.split(None, 1)[1]
            shellcode_asm = shellcraft.cat(filename)  # type: ignore
        else:
            raise ToolExecutionError(
                "Unsupported shellcode command. Supported: 'sh', 'cat <file>'."
            )

        return shellcode_asm
    except Exception as e:  # Catch PwnlibException or other issues
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
                # cyclic_find expects bytes for string patterns
                value_to_find = value_to_find.encode("utf-8")

            offset = cyclic_find(value_to_find, n=4)  # type: ignore
            logger.info(f"Found cyclic offset for '{input_data.find}': {offset}")
            return f"Offset for '{input_data.find}' is: {offset}"
        else:
            pattern_bytes = cyclic(input_data.length, n=4)  # type: ignore
            pattern = pattern_bytes.decode("utf-8", errors="ignore")
            logger.info(f"Generated {input_data.length}-byte cyclic pattern.")
            return f"Generated pattern: {pattern}"
    except Exception as e:  # Catch PwnlibException or other issues
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
        elf = ELF(input_data.file_path)  # type: ignore
        results = [
            f"File: {elf.path}",
            f"Arch: {elf.arch}",
            f"Bits: {elf.bits}",
            f"OS: {elf.os}",
            f"RELRO: {elf.relro}",  # type: ignore
            f"PIE: {elf.pie}",
            f"NX: {elf.nx}",
            f"Canary: {elf.canary}",
            f"Functions (first 10): {list(elf.functions.keys())[:10]}",
        ]
        return "\n".join(results)
    except FileNotFoundError:
        logger.error(f"ELF file not found: '{input_data.file_path}'")
        raise ToolExecutionError(f"ELF file not found: {input_data.file_path}")
    except Exception as e:  # Catch PwnlibException or other issues
        logger.error(f"Failed to inspect ELF file '{input_data.file_path}': {e}")
        raise ToolExecutionError(f"Failed to inspect ELF '{input_data.file_path}': {e}")


@register_tool(
    name="pwn_process_interaction",
    input_model=PwnProcessInteractionInput,
    description="Starts a local process and interacts with it by sending a payload.",
    tags=["pwn", "binary-analysis", "local", "security"],
    category="security",
    safe_mode=False,
)
def pwn_process_interaction(input_data: PwnProcessInteractionInput) -> str:
    """Starts a local process, sends it a payload, and returns the output.

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
    logger.info(f"Starting local process: {input_data.file_path}")
    p = None
    try:
        p = process(input_data.file_path)  # type: ignore
        p.sendline(input_data.payload.encode("utf-8"))
        response = p.recvall(timeout=input_data.timeout).decode(
            "utf-8", errors="ignore"
        )
        return response
    except FileNotFoundError:
        logger.error(
            f"Executable not found for pwn_process_interaction: '{input_data.file_path}'"
        )
        raise ToolExecutionError(f"Executable not found: {input_data.file_path}")
    except Exception as e:  # Catch PwnlibException or other issues
        logger.error(f"Process interaction failed for '{input_data.file_path}': {e}")
        raise ToolExecutionError(
            f"Process interaction failed for '{input_data.file_path}': {e}"
        )
    finally:
        if p:
            p.close()
