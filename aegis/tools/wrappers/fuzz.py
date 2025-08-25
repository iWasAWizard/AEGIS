# aegis/tools/wrappers/fuzz.py
# (complete file)
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
import shlex
from pathlib import Path
from typing import Dict, Any, List

import httpx
from pydantic import BaseModel, Field, ValidationError

# Import ToolExecutionError
from aegis.exceptions import ToolExecutionError, ToolNotFoundError
from aegis.registry import ToolEntry, register_tool, get_tool
from aegis.schemas.emoji import EMOJI_SET
from aegis.utils.logger import setup_logger
from aegis.utils.exec_common import run_subprocess

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
    allow_shell: bool = Field(
        False,
        description="If true, run via /bin/sh -lc; otherwise '{}' must be a standalone argv token.",
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
    allow_shell: bool = Field(
        False,
        description="If true, run via /bin/sh -lc; otherwise '{}' must be a standalone argv token.",
    )


class FuzzAPIRequestInput(BaseModel):
    """Input for fuzzing a JSON-based HTTP API."""

    url: str = Field(..., description="The target API endpoint URL.")
    method: str = Field(
        "POST", description="The HTTP method to use (e.g., 'POST', 'PUT')."
    )
    mode: str = Field("json", description="Payload mode for the request body.")
    iterations: int = Field(5, ge=1, description="Number of API requests to send.")


class FuzzToolRegistryInput(BaseModel):
    """Input for fuzzing internal tools in the AEGIS registry."""

    tool_name: str = Field(..., description="Registered tool name to invoke.")
    iterations: int = Field(5, ge=1, description="Number of calls to make.")
    mode: str = Field(
        "json",
        description="Payload mode. Valid: 'json' for dict-like, 'ascii'/'emoji'/'bytes' for free-form fields.",
    )


# === Utility: payload generators ===


def generate_payload(mode: str, max_len: int) -> str:
    mode = (mode or "ascii").lower()
    if mode == "ascii":
        return "".join(
            random.choice(string.ascii_letters + string.digits + string.punctuation)
            for _ in range(random.randint(1, max_len))
        )
    if mode == "emoji":
        return "".join(
            random.choice(EMOJI_SET) for _ in range(random.randint(1, max_len // 2 + 1))
        )
    if mode == "json":
        # produce noisy but valid-ish JSON-ish structure
        obj = {
            "s": "".join(
                random.choice(string.ascii_letters)
                for _ in range(random.randint(0, max_len // 2))
            ),
            "n": random.randint(-10_000, 10_000),
            "b": random.choice([True, False]),
            "arr": [random.randint(0, 100) for _ in range(random.randint(0, 10))],
        }
        return json.dumps(obj)
    if mode == "bytes":
        # return as latin-1 encodable string (caller decides how to write/encode)
        return "".join(
            chr(random.randint(0, 255)) for _ in range(random.randint(1, max_len))
        )
    # default
    return "".join(
        random.choice(string.ascii_letters + string.digits)
        for _ in range(random.randint(1, max_len))
    )


# === Tools ===


@register_tool(
    name="fuzz_external_command",
    input_model=FuzzExternalCommandInput,
    description="Run an external command multiple times with fuzzed inputs substituted into a template.",
    tags=["fuzz", "external", "command", "wrapper"],
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
            # Execute with central helper
            if input_data.allow_shell:
                exec_res = run_subprocess(
                    cmd, timeout=5, allow_shell=True, text_mode=True
                )
            else:
                # Safe path: '{}' must be a standalone argv token
                tokens = shlex.split(input_data.command)
                if "{}" not in tokens:
                    raise ToolExecutionError(
                        "When allow_shell=False, '{}' must be a standalone token in the command template."
                    )
                tokens = [payload if t == "{}" else t for t in tokens]
                exec_res = run_subprocess(
                    tokens, timeout=5, allow_shell=False, text_mode=True
                )
            results.append(
                {
                    "iteration": i + 1,
                    "input": payload,
                    "returncode": exec_res.returncode,
                    "stdout": exec_res.stdout_text(),
                    "stderr": exec_res.stderr_text(),
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
        tmp_file_name: str | None = None
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
            # Execute with central helper
            if input_data.allow_shell:
                exec_res = run_subprocess(
                    cmd, timeout=10, allow_shell=True, text_mode=True
                )
            else:
                tokens = shlex.split(input_data.command_template)
                if "{}" not in tokens:
                    raise ToolExecutionError(
                        "When allow_shell=False, '{}' must be a standalone token in the command template."
                    )
                tokens = [tmp_file_name if t == "{}" else t for t in tokens]
                exec_res = run_subprocess(
                    tokens, timeout=10, allow_shell=False, text_mode=True
                )
            results.append(
                {
                    "iteration": i + 1,
                    "file_content_preview": content[:100]
                    + ("..." if len(content) > 100 else ""),
                    "file_path": tmp_file_name,
                    "returncode": exec_res.returncode,
                    "stdout": exec_res.stdout_text(),
                    "stderr": exec_res.stderr_text(),
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
    description="Send fuzzed JSON bodies to an HTTP API endpoint.",
    tags=["fuzz", "api", "http", "wrapper"],
    category="wrapper",
    safe_mode=False,
)
def fuzz_api_request(input_data: FuzzAPIRequestInput) -> Dict[str, Any]:
    """Send fuzzed HTTP requests to a target API with varying payloads and methods.
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
        )  # keep API payloads moderate in size
        try:
            resp = httpx.request(
                method=input_data.method,
                url=input_data.url,
                json=json.loads(payload) if input_data.mode == "json" else payload,
                timeout=10.0,
            )
            results.append(
                {
                    "iteration": i + 1,
                    "status_code": resp.status_code,
                    "ok": resp.is_success,
                    "text_preview": resp.text[:200],
                }
            )
        except Exception as e:
            logger.exception(f"API fuzzing iteration {i + 1} failed.")
            results.append(
                {"iteration": i + 1, "error": str(e), "status_code": -1, "ok": False}
            )

    failures = sum(1 for r in results if not r.get("ok", False) or "error" in r)
    return {
        "summary": {"attempted": input_data.iterations, "failures": failures},
        "results": results,
    }


@register_tool(
    name="fuzz_tool_via_registry",
    input_model=FuzzToolRegistryInput,
    description="Invoke a registered AEGIS tool repeatedly with fuzzed inputs.",
    tags=["fuzz", "internal", "registry", "wrapper"],
    category="wrapper",
    safe_mode=False,
)
def fuzz_tool_via_registry(input_data: FuzzToolRegistryInput) -> Dict[str, Any]:
    """Invoke a registered AEGIS tool by name, supplying fuzzed inputs.
    This tool demonstrates how fuzzing can exercise tool schemas and validation.

    :param input_data: Configuration for internal tool fuzzing.
    :type input_data: FuzzToolRegistryInput
    :return: Summary of successes/failures across invocations.
    :rtype: Dict[str, Any]
    """
    logger.info(f"Fuzzing internal tool: {input_data.tool_name}")
    entry: ToolEntry | None = get_tool(input_data.tool_name)
    if not entry:
        raise ToolNotFoundError(f"Tool '{input_data.tool_name}' is not registered.")

    results: List[Dict[str, Any]] = []
    for i in range(input_data.iterations):
        try:
            # For 'json' mode, try to fuzz the model by partial dicts, else send a string payload
            if input_data.mode == "json" and entry.input_model:
                # naive model fuzz: keep fields optional-ish by skipping some
                sample = {}
                for fname, f in entry.input_model.model_fields.items():  # type: ignore[attr-defined]
                    if random.choice([True, False]):
                        # very naive: assign random text or small ints
                        sample[fname] = random.choice(
                            [
                                "".join(
                                    random.choice(string.ascii_letters)
                                    for _ in range(6)
                                ),
                                random.randint(0, 10),
                                True,
                                None,
                            ]
                        )
                res = entry.func(input_data=entry.input_model(**sample))  # type: ignore
            else:
                res = entry.func(input_data=generate_payload("ascii", 40))  # type: ignore

            results.append(
                {"iteration": i + 1, "ok": True, "result_preview": str(res)[:200]}
            )
        except ValidationError as ve:
            results.append(
                {
                    "iteration": i + 1,
                    "ok": False,
                    "error": "ValidationError",
                    "detail": str(ve)[:200],
                }
            )
        except Exception as e:
            logger.exception("Internal tool fuzzing iteration failed.")
            results.append(
                {
                    "iteration": i + 1,
                    "ok": False,
                    "error": type(e).__name__,
                    "detail": str(e)[:200],
                }
            )

    failures = sum(1 for r in results if not r.get("ok", False))
    return {
        "summary": {"attempted": input_data.iterations, "failures": failures},
        "results": results,
    }
