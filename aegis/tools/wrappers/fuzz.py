# aegis/tools/wrappers/fuzz.py
"""
Wrapper tools for performing fuzz testing on various targets.

This module provides tools to orchestrate fuzzing campaigns against external
command-line applications, file parsers, web APIs, and even internal tools
within the AEGIS registry.
"""

import json
import random
import string
import subprocess
import tempfile
from typing import Dict, Any, List, Optional

import requests
from pydantic import BaseModel, Field

from aegis.registry import TOOL_REGISTRY, ToolEntry, register_tool
from aegis.schemas.emoji import EMOJI_SET
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# === Input Models ===


class FuzzExternalCommandInput(BaseModel):
    """Input for fuzzing an external command-line tool.

    :ivar command: Command to run. Use '{}' as a placeholder for the fuzzed input.
    :vartype command: str
    :ivar mode: Payload mode: 'ascii', 'emoji', 'json', or 'bytes'.
    :vartype mode: str
    :ivar iterations: Number of fuzzing iterations to run.
    :vartype iterations: int
    :ivar max_length: Maximum length of the generated payload.
    :vartype max_length: int
    """

    command: str = Field(
        ...,
        description="Command to run. Use '{}' as a placeholder for the fuzzed input.",
    )
    mode: str = Field(
        "ascii", description="Payload mode: 'ascii', 'emoji', 'json', or 'bytes'."
    )
    iterations: int = Field(
        10, ge=1, le=100, description="Number of fuzzing iterations to run."
    )
    max_length: int = Field(
        100, ge=1, le=1000, description="Maximum length of the generated payload."
    )


class FuzzFileInputInput(BaseModel):
    """Input for fuzzing a tool that accepts a file as input.

    :ivar command_template: Command template with '{}' where the temporary file path should go.
    :vartype command_template: str
    :ivar file_mode: Payload mode for file content: 'ascii', 'emoji', or 'bytes'.
    :vartype file_mode: str
    :ivar max_length: Maximum length of the generated file content.
    :vartype max_length: int
    :ivar iterations: Number of temporary files to generate and test.
    :vartype iterations: int
    """

    command_template: str = Field(
        ...,
        description="Command template with '{}' where the temporary file path should go.",
    )
    file_mode: str = Field(
        "ascii",
        description="Payload mode for file content: 'ascii', 'emoji', or 'bytes'.",
    )
    max_length: int = Field(
        100, ge=1, description="Maximum length of the generated file content."
    )
    iterations: int = Field(
        5, ge=1, description="Number of temporary files to generate and test."
    )


class FuzzAPIRequestInput(BaseModel):
    """Input for fuzzing a web API endpoint.

    :ivar url: The target API endpoint URL.
    :vartype url: str
    :ivar method: The HTTP method to use (e.g., 'POST', 'PUT').
    :vartype method: str
    :ivar mode: Payload mode for the request body.
    :vartype mode: str
    :ivar iterations: Number of API requests to send.
    :vartype iterations: int
    """

    url: str = Field(..., description="The target API endpoint URL.")
    method: str = Field(
        "POST", description="The HTTP method to use (e.g., 'POST', 'PUT')."
    )
    mode: str = Field("json", description="Payload mode for the request body.")
    iterations: int = Field(5, ge=1, description="Number of API requests to send.")


class FuzzToolRegistryInput(BaseModel):
    """Input for fuzzing an internal tool from the AEGIS registry.

    :ivar tool_name: The name of the registered internal tool to fuzz.
    :vartype tool_name: str
    :ivar iterations: Number of times to invoke the tool with fuzzed input.
    :vartype iterations: int
    """

    tool_name: str = Field(
        ..., description="The name of the registered internal tool to fuzz."
    )
    iterations: int = Field(
        5, ge=1, description="Number of times to invoke the tool with fuzzed input."
    )


# === Helper Function ===


def generate_payload(mode: str, max_length: int) -> str:
    """Generates a random payload string based on the specified mode.

    :param mode: The type of payload to generate ('ascii', 'emoji', 'json', 'bytes').
    :type mode: str
    :param max_length: The maximum length of the payload.
    :type max_length: int
    :return: A randomly generated payload string.
    :rtype: str
    """
    length = random.randint(1, max_length)
    if mode == "ascii":
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))
    if mode == "emoji":
        return "".join(random.choices(EMOJI_SET, k=length // 2 or 1))
    if mode == "json":
        # Generate a simple, randomized JSON object string.
        return json.dumps(
            {f"key_{i}": random.randint(0, 999) for i in range(random.randint(1, 5))}
        )
    if mode == "bytes":
        # Generate a string of random bytes (0-255).
        return "".join(chr(random.randint(0, 255)) for _ in range(length))
    return "DEFAULT_FUZZ_PAYLOAD"


# === Tools ===


@register_tool(
    name="fuzz_external_command",
    input_model=FuzzExternalCommandInput,
    description="Fuzz an external shell command by injecting randomized payloads as arguments.",
    tags=["fuzz", "external", "cli", "wrapper"],
    category="wrapper",
    safe_mode=False,
)
def fuzz_external_command(input_data: FuzzExternalCommandInput) -> Dict[str, Any]:
    """Runs a command multiple times with randomly generated string inputs.

    :param input_data: Configuration for the fuzzing session.
    :type input_data: FuzzExternalCommandInput
    :return: A dictionary summarizing the results, including failures and individual run details.
    :rtype: Dict[str, Any]
    """
    logger.info(f"Starting external command fuzzing for: {input_data.command}")
    results: List[Dict[str, Any]] = []
    for i in range(input_data.iterations):
        payload = generate_payload(input_data.mode, input_data.max_length)
        cmd = input_data.command.replace("{}", payload)
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=5, text=True, check=False
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input": payload,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        except Exception as e:
            logger.exception(f"Fuzzing iteration {i + 1} failed with an exception.")
            results.append({"iteration": i + 1, "input": payload, "error": str(e)})

    failures = sum(1 for r in results if r.get("returncode", 0) != 0 or "error" in r)
    return {
        "summary": {"attempted": input_data.iterations, "failures": failures},
        "results": results,
    }


@register_tool(
    name="fuzz_file_input",
    input_model=FuzzFileInputInput,
    description="Generate temporary files with fuzzed content and run a shell command on each.",
    tags=["fuzz", "file", "external", "wrapper"],
    category="wrapper",
    safe_mode=False,
)
def fuzz_file_input(input_data: FuzzFileInputInput) -> Dict[str, Any]:
    """Tests a command that takes a file path by feeding it randomly generated files.

    :param input_data: Configuration for the file fuzzing session.
    :type input_data: FuzzFileInputInput
    :return: A dictionary summarizing the results of each file-based execution.
    :rtype: Dict[str, Any]
    """
    logger.info(f"Starting file input fuzzing for: {input_data.command_template}")
    results: List[Dict[str, Any]] = []
    for i in range(input_data.iterations):
        content = generate_payload(input_data.file_mode, input_data.max_length)
        with tempfile.NamedTemporaryFile("w+", delete=True, suffix=".fuzz") as tmp:
            tmp.write(content)
            tmp.seek(0)
            cmd = input_data.command_template.replace("{}", tmp.name)
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    timeout=5,
                    text=True,
                    check=False,
                )
                results.append(
                    {
                        "iteration": i + 1,
                        "file_content": content[:100] + "...",
                        "returncode": proc.returncode,
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                    }
                )
            except Exception as e:
                logger.exception(
                    f"File fuzzing iteration {i + 1} failed with an exception."
                )
                results.append({"iteration": i + 1, "error": str(e)})

    failures = sum(1 for r in results if r.get("returncode", 0) != 0 or "error" in r)
    return {
        "summary": {"files_tested": input_data.iterations, "failures": failures},
        "results": results,
    }


@register_tool(
    name="fuzz_api_request",
    input_model=FuzzAPIRequestInput,
    description="Send fuzzed payloads to an HTTP API endpoint.",
    tags=["fuzz", "api", "network", "wrapper"],
    category="wrapper",
    safe_mode=False,
)
def fuzz_api_request(input_data: FuzzAPIRequestInput) -> Dict[str, Any]:
    """Sends multiple HTTP requests with fuzzed bodies to a target URL.

    :param input_data: Configuration for the API fuzzing session.
    :type input_data: FuzzAPIRequestInput
    :return: A dictionary summarizing the status codes and responses from the API.
    :rtype: Dict[str, Any]
    """
    logger.info(
        f"Starting API request fuzzing for: {input_data.method} {input_data.url}"
    )
    results: List[Dict[str, Any]] = []
    for i in range(input_data.iterations):
        payload = generate_payload(input_data.mode, 200)
        try:
            resp = requests.request(
                method=input_data.method,
                url=input_data.url,
                headers={"Content-Type": "application/json"},
                data=payload,
                timeout=10,
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input_payload": payload,
                    "status_code": resp.status_code,
                    "response_body": resp.text.strip(),
                }
            )
        except Exception as e:
            logger.exception(f"API fuzzing iteration {i + 1} failed with an exception.")
            results.append(
                {"iteration": i + 1, "input_payload": payload, "error": str(e)}
            )

    failures = sum(
        1 for r in results if r.get("status_code", 200) >= 400 or "error" in r
    )
    return {
        "summary": {"requests_sent": input_data.iterations, "failures": failures},
        "results": results,
    }


@register_tool(
    name="fuzz_tool_via_registry",
    input_model=FuzzToolRegistryInput,
    description="Fuzzes an internal AEGIS tool by calling it with default-constructed Pydantic models.",
    tags=["fuzz", "internal", "registry", "wrapper"],
    category="wrapper",
    safe_mode=True,
)
def fuzz_tool_via_registry(input_data: FuzzToolRegistryInput) -> Dict[str, Any]:
    """Attempts to call an internal tool with an empty/default input model.

    This is a basic smoke test to see if a tool can handle default or empty inputs
    without crashing. It is most effective on tools whose input models have
    optional fields or fields with default values.

    :param input_data: An object containing the name of the tool to fuzz.
    :type input_data: FuzzToolRegistryInput
    :return: A dictionary summarizing the results of the invocations.
    :rtype: Dict[str, Any]
    """
    logger.info(f"Fuzzing internal tool via registry: {input_data.tool_name}")
    tool_entry: Optional[ToolEntry] = TOOL_REGISTRY.get(input_data.tool_name)
    if not tool_entry:
        raise ValueError(f"No tool named '{input_data.tool_name}' is registered.")

    results: List[Dict[str, Any]] = []
    for i in range(input_data.iterations):
        try:
            # Construct a default instance of the tool's input model.
            # This will fail if the model has required fields without defaults.
            model_instance = tool_entry.input_model()
            output = tool_entry.run(model_instance)
            results.append(
                {
                    "iteration": i + 1,
                    "input": model_instance.model_dump(),
                    "output": str(output),
                }
            )
        except Exception as e:
            logger.exception(f"Internal tool fuzzing iteration {i + 1} failed.")
            results.append(
                {"iteration": i + 1, "input": "default model", "error": str(e)}
            )

    failures = sum(1 for r in results if "error" in r)
    return {
        "summary": {"invocations": input_data.iterations, "failures": failures},
        "results": results,
    }
