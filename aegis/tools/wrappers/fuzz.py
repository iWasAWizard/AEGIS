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
from pathlib import Path

import requests
from pydantic import BaseModel, Field, ValidationError

from aegis.registry import TOOL_REGISTRY, ToolEntry, register_tool, get_tool
from aegis.schemas.emoji import EMOJI_SET
from aegis.utils.logger import setup_logger

# Import ToolExecutionError
from aegis.exceptions import ToolExecutionError, ToolNotFoundError

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
    logger.warning(f"Unknown payload generation mode '{mode}'. Using default.")
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
    This tool returns a summary of results and does not raise ToolExecutionError for
    individual command failures, as that's expected in fuzzing. It will raise
    ToolExecutionError for setup issues (e.g., command template invalid).

    :param input_data: Configuration for the fuzzing session.
    :type input_data: FuzzExternalCommandInput
    :return: A dictionary summarizing the results, including failures and individual run details.
    :rtype: Dict[str, Any]
    :raises ToolExecutionError: If the command template is malformed.
    """
    if "{}" not in input_data.command:
        raise ToolExecutionError(
            "Command template must include '{}' placeholder for fuzzed input."
        )

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
        except subprocess.TimeoutExpired:
            logger.warning(
                f"Fuzzing iteration {i + 1} with input '{payload}' timed out."
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input": payload,
                    "error": "TimeoutExpired",
                    "returncode": -1,
                }
            )
        except Exception as e:  # Catch other subprocess errors
            logger.exception(
                f"Fuzzing iteration {i + 1} with input '{payload}' failed with an exception."
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input": payload,
                    "error": str(e),
                    "returncode": -1,
                }
            )

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
    This tool returns a summary. It will raise ToolExecutionError for setup issues.

    :param input_data: Configuration for the file fuzzing session.
    :type input_data: FuzzFileInputInput
    :return: A dictionary summarizing the results of each file-based execution.
    :rtype: Dict[str, Any]
    :raises ToolExecutionError: If the command template is malformed.
    """
    if "{}" not in input_data.command_template:
        raise ToolExecutionError(
            "Command template must include '{}' placeholder for the fuzzed file path."
        )

    logger.info(f"Starting file input fuzzing for: {input_data.command_template}")
    results: List[Dict[str, Any]] = []
    for i in range(input_data.iterations):
        content = generate_payload(input_data.file_mode, input_data.max_length)
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                "w+",
                delete=False,
                suffix=".fuzz",
                encoding="utf-8",
                errors="surrogateescape",
            ) as tmp:
                tmp_file_name = tmp.name
                tmp.write(content)
                # Must flush and seek for the external process to see the content.
                tmp.flush()
                tmp.seek(0)

            # tmp is now closed, but file still exists due to delete=False
            cmd = input_data.command_template.replace("{}", tmp_file_name)
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                timeout=10,  # Increased timeout for file I/O + command
                text=True,
                check=False,
                encoding="utf-8",
                errors="surrogateescape",
            )
            results.append(
                {
                    "iteration": i + 1,
                    "file_content_preview": content[:100]
                    + ("..." if len(content) > 100 else ""),
                    "file_path": tmp_file_name,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                }
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                f"File fuzzing iteration {i + 1} with file content '{content[:50]}...' timed out."
            )
            results.append(
                {
                    "iteration": i + 1,
                    "error": "TimeoutExpired",
                    "returncode": -1,
                    "file_path": tmp_file_name if tmp_file_name else "N/A",
                }
            )
        except Exception as e:
            logger.exception(
                f"File fuzzing iteration {i + 1} failed with an exception."
            )
            results.append(
                {
                    "iteration": i + 1,
                    "error": str(e),
                    "returncode": -1,
                    "file_path": tmp_file_name if tmp_file_name else "N/A",
                }
            )
        finally:
            if tmp_file_name and Path(tmp_file_name).exists():
                try:
                    Path(tmp_file_name).unlink()
                except Exception as e_del:
                    logger.error(
                        f"Failed to delete temporary fuzz file {tmp_file_name}: {e_del}"
                    )

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
    This tool returns a summary. It will raise ToolExecutionError for critical setup issues.

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
        payload = generate_payload(
            input_data.mode, 200
        )  # Max length 200 for API payloads
        try:
            # Use data=payload for non-JSON, json=payload_dict for JSON
            request_kwargs = {
                "method": input_data.method,
                "url": input_data.url,
                "timeout": 10,
            }
            if input_data.mode == "json":
                try:
                    payload_dict = json.loads(payload)
                    request_kwargs["json"] = payload_dict
                except json.JSONDecodeError:
                    # If JSON mode but payload isn't valid JSON (e.g. if generate_payload was modified)
                    # send as raw data. Or we could skip/error.
                    request_kwargs["data"] = payload.encode(
                        "utf-8", errors="surrogateescape"
                    )
                    request_kwargs["headers"] = {
                        "Content-Type": "text/plain"
                    }  # Indicate it's not JSON
            else:  # ascii, emoji, bytes
                request_kwargs["data"] = payload.encode(
                    "utf-8", errors="surrogateescape"
                )
                request_kwargs["headers"] = {
                    "Content-Type": (
                        "application/octet-stream"
                        if input_data.mode == "bytes"
                        else "text/plain"
                    )
                }

            resp = requests.request(**request_kwargs)  # type: ignore
            results.append(
                {
                    "iteration": i + 1,
                    "input_payload": payload,
                    "status_code": resp.status_code,
                    "response_body_preview": resp.text.strip()[:200]
                    + ("..." if len(resp.text.strip()) > 200 else ""),
                }
            )
        except requests.exceptions.Timeout:
            logger.warning(
                f"API fuzzing iteration {i + 1} with payload '{payload[:50]}...' timed out."
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input_payload": payload,
                    "error": "Timeout",
                    "status_code": -1,
                }
            )
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"API fuzzing iteration {i + 1} failed with a RequestException: {e}"
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input_payload": payload,
                    "error": str(e),
                    "status_code": -1,
                }
            )
        except Exception as e:  # Catch other unexpected errors
            logger.exception(
                f"API fuzzing iteration {i + 1} failed with an unexpected exception."
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input_payload": payload,
                    "error": str(e),
                    "status_code": -1,
                }
            )

    failures = sum(
        1
        for r in results
        if r.get("status_code", 200) >= 400
        or r.get("status_code", 200) == -1
        or "error" in r
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
    safe_mode=True,  # Fuzzing itself is a read-only operation on the tool's definition
)
def fuzz_tool_via_registry(input_data: FuzzToolRegistryInput) -> Dict[str, Any]:
    """Attempts to call an internal tool with an empty/default input model.
    This tool returns a summary. It will raise ToolExecutionError for setup issues
    (e.g., tool not found, or if the target tool's input model CANNOT be default constructed).

    This is a basic smoke test to see if a tool can handle default or empty inputs
    without crashing. It is most effective on tools whose input models have
    optional fields or fields with default values.

    :param input_data: An object containing the name of the tool to fuzz.
    :type input_data: FuzzToolRegistryInput
    :return: A dictionary summarizing the results of the invocations.
    :rtype: Dict[str, Any]
    :raises ToolExecutionError: If the tool is not found or its input model cannot be default-constructed.
    """
    logger.info(f"Fuzzing internal tool via registry: {input_data.tool_name}")

    try:
        # Use get_tool to ensure safe_mode checks are respected if this fuzz tool
        # were ever run in a context where safe_mode=True mattered for the target.
        # For this specific fuzz tool, it's generally okay to fuzz unsafe tools too,
        # as we are just constructing their input model.
        tool_entry: ToolEntry = get_tool(input_data.tool_name, safe_mode=False)
    except ToolNotFoundError as e:
        raise ToolExecutionError(f"Cannot fuzz tool: {e}")

    results: List[Dict[str, Any]] = []
    for i in range(input_data.iterations):
        model_instance = None
        try:
            # Construct a default instance of the tool's input model.
            # This will fail if the model has required fields without defaults.
            model_instance = tool_entry.input_model()
            # We don't actually run the tool here, as that could be unsafe
            # and is not the purpose of *this specific* fuzzing tool.
            # This tool only checks if default construction of input model works.
            # A different fuzz tool could be made to actually *run* with fuzzed inputs.
            output_str = f"Successfully default-constructed input model: {tool_entry.input_model.__name__}"
            results.append(
                {
                    "iteration": i + 1,
                    "input_model_type": tool_entry.input_model.__name__,
                    "default_constructed_input": model_instance.model_dump_json(
                        indent=2
                    ),
                    "outcome": output_str,
                }
            )
        except (
            ValidationError
        ) as ve:  # If default construction fails due to required fields
            logger.warning(
                f"Internal tool fuzzing (default construction) iteration {i + 1} failed for {input_data.tool_name}: {ve}"
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input_model_type": tool_entry.input_model.__name__,
                    "error": f"Pydantic ValidationError on default construction: {ve}",
                }
            )
            # This is an expected outcome for some models, so we don't re-raise ToolExecutionError here.
            # The summary will show it as a "failure" for this specific test type.
        except Exception as e:  # Other unexpected errors during model instantiation
            logger.exception(
                f"Internal tool fuzzing (default model instantiation) iteration {i + 1} failed for {input_data.tool_name} with unexpected error."
            )
            results.append(
                {
                    "iteration": i + 1,
                    "input_model_type": tool_entry.input_model.__name__,
                    "error": str(e),
                }
            )

    failures = sum(1 for r in results if "error" in r)
    return {
        "summary": {
            "invocations_attempted": input_data.iterations,
            "construction_failures": failures,
        },
        "results": results,
    }
