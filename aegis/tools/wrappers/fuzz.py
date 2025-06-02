import json
import os
import random
import string
import subprocess
import tempfile

import requests
from pydantic import BaseModel, Field

from aegis.registry import TOOL_REGISTRY
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class FuzzExternalCommandInput(BaseModel):
    """
    Represents the FuzzExternalCommandInput class.

    Defines input options for fuzzing external CLI tools by randomly varying command-line arguments or input files.
    """

    command: str = Field(
        ..., description="Command to run. Use '{}' as placeholder for fuzz input."
    )
    mode: str = Field("ascii", description="Payload mode: ascii, emoji, json, bytes")
    iterations: int = Field(10, ge=1, le=100)
    max_length: int = Field(100, ge=1, le=1000)


class FuzzFileInputInput(BaseModel):
    """
    Represents the FuzzFileInputInput class.

    Specifies file paths and variation patterns for fuzz testing file readers or parsers.
    """

    command_template: str = Field(
        ..., description="Command with '{}' where the temp file path should go."
    )
    file_mode: str = Field("ascii", description="ascii, emoji, bytes")
    max_length: int = Field(100, ge=1)
    iterations: int = Field(5, ge=1)


class FuzzAPIRequestInput(BaseModel):
    """
    Represents the FuzzAPIRequestInput class.

    Used to describe endpoints, headers, and payload templates for fuzzing web APIs.
    """

    url: str = Field(..., description="API endpoint URL")
    method: str = Field("POST", description="HTTP method")
    mode: str = Field("json", description="Payload mode")
    iterations: int = Field(5, ge=1)


class FuzzToolRegistryInput(BaseModel):
    """
    Represents the FuzzToolRegistryInput class.

    Contains configuration for fuzz testing internal tools by varying tool inputs based on the system's tool registry.
    """

    tool_name: str = Field(
        ..., description="Name of the internal tool to fuzz from registry"
    )
    iterations: int = Field(5, ge=1)


def generate_payload(mode: str, max_length: int):
    """
    generate_payload.
    :param mode: Description of mode
    :param max_length: Description of max_length
    :type mode: Any
    :type max_length: Any
    :return: Description of return value
    :rtype: Any
    """
    if mode == "ascii":
        return "".join(
            random.choices(
                string.ascii_letters + string.digits, k=random.randint(1, max_length)
            )
        )
    if mode == "emoji":
        from aegis.schemas.emoji import EMOJI_SET

        return "".join(random.choices(EMOJI_SET, k=random.randint(1, max_length // 2)))
    if mode == "json":
        return json.dumps(
            {f"k{i}": random.randint(0, 999) for i in range(random.randint(1, 5))}
        )
    if mode == "bytes":
        return "".join(
            (chr(random.randint(0, 255)) for _ in range(random.randint(1, max_length)))
        )
    return "FUZZ"


@register_tool(
    name="fuzz_external_command",
    input_model=FuzzExternalCommandInput,
    description="Fuzz an external shell command using randomized payloads."
                "Replace '{}' in the command with generated input.",
    tags=["fuzz", "external", "cli"],
    category="wrapper",
    safe_mode=False,
)
def fuzz_external_command(input_data: FuzzExternalCommandInput) -> dict:
    """
    fuzz_external_command.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("Starting external command fuzzing")
    logger.debug(f"Command template: {input_data.command}")
    results = []
    for i in range(input_data.iterations):
        payload = generate_payload(input_data.mode, input_data.max_length)
        cmd = input_data.command.replace("{}", payload)
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=5, text=True
            )
            results.append(
                {
                    "command": cmd,
                    "input": payload,
                    "returncode": result.returncode,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                }
            )
        except Exception as e:
            logger.exception(f"[fuzz_external_command] Iteration {i} failed")
            results.append({"command": cmd, "input": payload, "error": str(e)})
    return {
        "summary": {
            "attempted": input_data.iterations,
            "failures": sum(
                (1 for r in results if r.get("returncode", 0) != 0 or "error" in r)
            ),
        },
        "results": results,
    }


@register_tool(
    name="fuzz_file_input",
    input_model=FuzzFileInputInput,
    description="Generate temporary files with fuzzed content and run a shell command on each.",
    tags=["fuzz", "file", "external"],
    category="wrapper",
    safe_mode=False,
)
def fuzz_file_input(input_data: FuzzFileInputInput) -> dict:
    """
    fuzz_file_input.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("Starting file input fuzzing")
    logger.debug(f"Command template: {input_data.command_template}")
    results = []
    for i in range(input_data.iterations):
        content = generate_payload(input_data.file_mode, input_data.max_length)
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        cmd = input_data.command_template.replace("{}", tmp_path)
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=5, text=True
            )
            results.append(
                {
                    "file": tmp_path,
                    "content": content,
                    "command": cmd,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip(),
                }
            )
        except Exception as e:
            logger.exception(f"[fuzz_file_input] Iteration {i} failed")
            results.append({"file": tmp_path, "command": cmd, "error": str(e)})
        os.unlink(tmp_path)
    return {"summary": {"files_tested": input_data.iterations}, "results": results}


@register_tool(
    name="fuzz_api_request",
    input_model=FuzzAPIRequestInput,
    description="Send fuzzed payloads to an HTTP API endpoint.",
    tags=["fuzz", "api", "network"],
    category="wrapper",
    safe_mode=False,
)
def fuzz_api_request(input_data: FuzzAPIRequestInput) -> dict:
    """
    fuzz_api_request.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info("Starting API request fuzzing")
    logger.debug(f"Target URL: {input_data.url}, Method: {input_data.method}")
    results = []
    for i in range(input_data.iterations):
        payload = generate_payload(input_data.mode, 200)
        try:
            resp = requests.request(
                method=input_data.method,
                url=input_data.url,
                headers={"Content-Type": "application/json"},
                data=payload,
            )
            results.append(
                {
                    "input": payload,
                    "status": resp.status_code,
                    "response": resp.text.strip(),
                }
            )
        except Exception as e:
            logger.exception(f"[fuzz_api_request] Iteration {i} failed")
            results.append({"input": payload, "error": str(e)})
    return {"summary": {"requests_sent": input_data.iterations}, "results": results}


@register_tool(
    name="fuzz_tool_via_registry",
    input_model=FuzzToolRegistryInput,
    description="Call an internal tool using randomized valid inputs (if guessable).",
    tags=["fuzz", "internal", "registry"],
    category="wrapper",
    safe_mode=True,
)
def fuzz_tool_via_registry(input_data: FuzzToolRegistryInput) -> dict:
    """
    fuzz_tool_via_registry.
    :param input_data: Description of input_data
    :type input_data: Any
    :return: Description of return value
    :rtype: Any
    """
    logger.info(f"Fuzzing tool via registry: {input_data.tool_name}")
    name = input_data.tool_name
    tool_entry = TOOL_REGISTRY.get(name)
    if not tool_entry:
        raise ValueError(f"No tool named '{name}' registered.")
    results = []
    for i in range(input_data.iterations):
        model = tool_entry.input_model
        try:
            fuzzed = model.construct()
            output = tool_entry.func(fuzzed)
            results.append({"input": fuzzed.dict(), "output": output})
        except Exception as e:
            logger.exception(f"[fuzz_tool_via_registry] Iteration {i} failed")
            results.append({"input": {}, "error": str(e)})
    return {"summary": {"invocations": input_data.iterations}, "results": results}
