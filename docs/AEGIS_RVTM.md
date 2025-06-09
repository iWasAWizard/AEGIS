# AEGIS Requirements Verification Traceability Matrix (RVTM)

This document outlines all verifiable requirements for the AEGIS system, including their sources and verification methods.

| Requirement ID | Requirement Description | Source | Verification Method |
|----------------|-------------------------|--------|----------------------|
| REQ-001 | The system shall support command-line interface (CLI) execution for initiating agent tasks with task prompts and configuration files. | aegis/cli.py | Test |
| REQ-002 | The system shall provide a registry that validates and stores metadata for each registered tool, rejecting tools with incomplete metadata. | aegis/registry.py | Test |
| REQ-003 | Each registered tool shall include structured metadata fields: name, description, input model, and tags. | aegis/tools/tool_metadata.py | Test |
| REQ-004 | The agent shall be able to execute wrapper tools that call one or more primitive tools and expose composite functionality. | aegis/tools/wrappers/ | Demonstration |
| REQ-005 | The agent shall be able to execute primitive tools that perform discrete operations on the host system (e.g., file operations, network checks). | aegis/tools/primitives/ | Test |
| REQ-006 | Each tool shall expose a list of tags and one or more categories that can be filtered at runtime. | aegis/tools/tool_metadata.yaml | Test |
| REQ-007 | The system shall load execution presets from YAML files and apply them to agent runs at runtime. | aegis/presets.yaml | Test |
| REQ-008 | The system shall build and launch in a Docker container using provided Dockerfile and docker-compose.yml without manual configuration. | docker-compose.yml, Dockerfile | Demonstration |
| REQ-009 | The system shall expose a web dashboard that can be accessed over HTTP and return active task state information. | aegis/serve_dashboard.py | Test |
| REQ-010 | The system shall reject any tool registration that lacks complete or valid metadata fields at import time. | aegis/registry.py | Test |
| REQ-011 | All tool input schemas shall be defined using type-validated Pydantic models and raise exceptions on invalid input. | aegis/types.py | Test |
| REQ-012 | The system shall load environment variables from a `.env` file when running via Docker Compose. | .env, .env.example, docker-compose.yml | Test |
| REQ-013 | The agent shall support executing tools in safe mode, which blocks execution of tools marked as unsafe. | aegis/registry.py | Test |
| REQ-014 | The system shall include a unified runner that can load a preset and launch an agent graph from a specified task prompt. | aegis/runner.py | Test |
| REQ-015 | The system shall execute agent workflows defined as graphs in YAML presets, transitioning deterministically between nodes. | aegis/runner.py, aegis/presets.yaml | Test |
| REQ-016 | The system shall dynamically route tool execution requests to registered tool instances based on name and metadata. | aegis/tools/routing.py | Test |
| REQ-017 | The browser wrapper tools shall support capturing and returning a full DOM snapshot from a target webpage. | aegis/tools/wrappers/browser/capture_web_state.py | Demonstration |
| REQ-018 | The browser tools shall execute user-defined interaction sequences including element clicking, typing, and waiting. | aegis/tools/wrappers/browser/web_interact.py | Demonstration |
| REQ-019 | The agent shall be able to compare DOM snapshots of two webpages and return a summary of differences. | aegis/tools/wrappers/browser/web_snapshot_compare.py | Test |
| REQ-020 | Each tool's metadata shall include tag and category fields that can be queried by agents or runtime filters. | aegis/tools/tool_metadata.yaml | Test |
| REQ-021 | The system shall support integration tools that invoke multiple primitives or wrappers to execute composite tasks. | aegis/tools/wrappers/integration.py | Demonstration |
| REQ-022 | The fuzzing toolset shall support randomized command-line input generation for a given binary or shell interface. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-023 | The network primitive tools shall allow agents to scan open ports, resolve domain names, and check host reachability. | aegis/tools/primitives/primitive_network.py | Test |
| REQ-024 | The filesystem primitive tools shall support listing, creating, deleting, and modifying files and directories. | aegis/tools/primitives/primitive_filesystem.py | Test |
| REQ-025 | The chaos tools shall simulate failure modes such as file deletion, resource exhaustion, or random delays. | aegis/tools/primitives/chaos.py | Demonstration |
| REQ-026 | The agent shall prevent execution of any tool marked as unsafe when safe mode is enabled. | aegis/registry.py | Test |
| REQ-027 | The system shall allow each tool to define a timeout period, after which execution shall be forcibly terminated. | aegis/registry.py | Test |
| REQ-028 | The system shall retry tool execution a specified number of times if failures occur and retries are enabled. | aegis/registry.py | Test |
| REQ-029 | The agent shall generate logs for each executed step, including tool name, input, output, and timestamps. | aegis/runner.py, aegis/registry.py | Test |
| REQ-030 | The system shall initialize and expose a task ID and prompt for each agent run. | aegis/runner.py | Test |
| REQ-031 | The system shall expose a web route to launch agent tasks via HTTP request with task parameters. | aegis/serve_dashboard.py | Test |
| REQ-032 | The agent shall return its final output as a structured response after completing execution. | aegis/runner.py | Test |
| REQ-033 | The system shall load a machine manifest from a YAML file and make its contents accessible to agent logic. | machines.yaml, aegis/runner.py | Test |
| REQ-034 | The system shall enforce that each YAML preset includes an initial state and valid node transitions. | aegis/presets.yaml | Test |
| REQ-035 | The CLI shall return a non-zero exit code if the agent fails to complete execution. | aegis/cli.py | Test |
| REQ-036 | The agent shall validate each tool’s input against its Pydantic schema before execution and raise an error on failure. | aegis/registry.py, aegis/types.py | Test |
| REQ-037 | The system shall log every tool execution failure with the exception message and tool name. | aegis/registry.py, aegis/runner.py | Test |
| REQ-038 | The agent shall allow disabling safe mode on a per-tool basis when explicitly marked as overridden. | aegis/registry.py | Test |
| REQ-039 | The system shall provide structured logging with machine-readable fields for tool execution events. | aegis/registry.py | Test |
| REQ-040 | The runner shall support multiple agent graphs based on different presets stored in the configuration directory. | aegis/runner.py, aegis/presets.yaml | Test |
| REQ-041 | Each agent graph shall declare its nodes and transitions using valid syntax and resolvable tool names. | aegis/presets.yaml | Test |
| REQ-042 | The system shall initialize and inject the `llm_query` function into agent execution context when required. | aegis/runner.py | Test |
| REQ-043 | The system shall expose a shell wrapper tool capable of executing a specified shell command and capturing output. | aegis/tools/wrappers/shell.py | Test |
| REQ-044 | The shell tool shall sanitize user input to prevent command injection or shell escapes. | aegis/tools/wrappers/shell.py | Test |
| REQ-045 | The system shall allow tools to declare themselves as sensors (passive), actions (active), or integrations (composite). | aegis/tools/tool_metadata.yaml | Test |
| REQ-046 | The LLM wrapper tool shall return a string response given a valid prompt input. | aegis/tools/wrappers/llm.py | Test |
| REQ-047 | The LLM wrapper shall reject input if the prompt exceeds the token limit. | aegis/tools/wrappers/llm.py | Test |
| REQ-048 | The agent shall retry a tool if the tool raises a transient exception and retries are configured. | aegis/registry.py | Test |
| REQ-049 | The system shall return an HTTP 200 response when the web dashboard endpoint is queried successfully. | aegis/serve_dashboard.py | Test |
| REQ-050 | The integration wrapper tool shall validate its dependencies before attempting composed execution. | aegis/tools/wrappers/integration.py | Test |
| REQ-051 | The system shall reject malformed YAML presets and raise a validation error with diagnostic feedback. | aegis/presets.yaml | Test |
| REQ-052 | The filesystem wrapper tool shall support batch operations over multiple paths (e.g., delete, list, copy). | aegis/tools/wrappers/wrapper_filesystem.py | Test |
| REQ-053 | The network wrapper shall return structured results from operations such as port scans or HTTP checks. | aegis/tools/wrappers/wrapper_network.py | Test |
| REQ-054 | The system shall raise a descriptive error if a required environment variable is not set at runtime. | .env, aegis/runner.py | Test |
| REQ-055 | The runner shall emit a structured result object summarizing each tool’s outcome after agent completion. | aegis/runner.py | Test |
| REQ-056 | The system shall expose a fuzzing wrapper tool that accepts a shell command template and substitutes randomized inputs. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-057 | The fuzzing tool shall log each input used during a fuzz session along with execution results or errors. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-058 | Each tool execution shall be timestamped and logged with start and end time for runtime tracing. | aegis/registry.py | Test |
| REQ-059 | The browser tools shall support configuring wait durations before interacting with webpage elements. | aegis/tools/wrappers/browser/web_interact.py | Test |
| REQ-060 | The browser snapshot tool shall raise an error if the target webpage fails to load. | aegis/tools/wrappers/browser/web_snapshot_compare.py | Test |
| REQ-061 | The system shall include a helper utility to convert file paths to absolute paths when required by tools. | aegis/tools/wrappers/wrapper_filesystem.py | Test |
| REQ-062 | The agent shall reject execution of tools with malformed or missing Pydantic input schemas. | aegis/types.py, aegis/registry.py | Test |
| REQ-063 | The filesystem primitive tool shall fail gracefully when attempting to access a non-existent path. | aegis/tools/primitives/primitive_filesystem.py | Test |
| REQ-064 | The network primitive tool shall timeout after a configurable period when a target host is unreachable. | aegis/tools/primitives/primitive_network.py | Test |
| REQ-065 | The shell wrapper shall redact environment-sensitive variables in logs by default unless explicitly allowed. | aegis/tools/wrappers/shell.py | Test |
| REQ-066 | The registry shall prevent tool registration at import time if any required metadata field is missing or invalid. | aegis/registry.py | Test |
| REQ-067 | The registry shall support dynamic inspection of registered tools and return metadata including name, tags, and categories. | aegis/registry.py | Test |
| REQ-068 | The shell wrapper shall enforce character limits on command strings and raise an error when exceeded. | aegis/tools/wrappers/shell.py | Test |
| REQ-069 | The browser interaction tool shall raise an error if a targeted element is not found after the specified wait. | aegis/tools/wrappers/browser/web_interact.py | Test |
| REQ-070 | The agent shall enforce consistent output schema across all tool executions, including success flag and output payload. | aegis/runner.py, aegis/registry.py | Test |
| REQ-071 | The agent shall propagate execution context (e.g., task ID, safe mode) to each tool invocation. | aegis/runner.py, aegis/registry.py | Test |
| REQ-072 | The filesystem wrapper shall allow read, write, and append operations on specified file paths. | aegis/tools/wrappers/wrapper_filesystem.py | Test |
| REQ-073 | The registry shall enforce per-tool retry configuration and track retry counts per invocation. | aegis/registry.py | Test |
| REQ-074 | The agent shall expose an optional debug mode that increases logging verbosity and trace detail. | aegis/runner.py | Test |
| REQ-075 | The runner shall validate agent graph configuration before execution and reject invalid topologies. | aegis/runner.py, aegis/presets.yaml | Test |
| REQ-076 | The agent shall raise an error if a referenced tool in a preset graph is not registered at runtime. | aegis/runner.py, aegis/presets.yaml | Test |
| REQ-077 | The system shall support environment substitution in preset files using values from the `.env` file. | aegis/runner.py, .env | Test |
| REQ-078 | The agent shall support structured invocation from external systems using a FastAPI-compatible HTTP endpoint. | aegis/serve_dashboard.py | Test |
| REQ-079 | The HTTP launch endpoint shall accept a JSON payload including task prompt, graph configuration, and optional parameters. | aegis/serve_dashboard.py | Test |
| REQ-080 | The agent shall return a machine-readable final report over HTTP upon completion of a launched task. | aegis/serve_dashboard.py, aegis/runner.py | Test |
| REQ-081 | The registry shall track and expose tool categories, including sensor, action, and integration types. | aegis/registry.py, aegis/tools/tool_metadata.yaml | Test |
| REQ-082 | The fuzzing wrapper shall support configuring input types, such as numeric, alphanumeric, or emoji-based. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-083 | The filesystem primitive shall raise a permission error if write operations are attempted in read-only paths. | aegis/tools/primitives/primitive_filesystem.py | Test |
| REQ-084 | The network wrapper shall raise a timeout exception if a response is not received within the configured window. | aegis/tools/wrappers/wrapper_network.py | Test |
| REQ-085 | The LLM wrapper shall allow users to configure a specific model backend and reject unknown models. | aegis/tools/wrappers/llm.py | Test |
| REQ-086 | The agent shall reject a launch request if the input JSON payload is missing required fields. | aegis/serve_dashboard.py | Test |
| REQ-087 | The registry shall emit an error log and raise an exception if a tool fails validation at registration time. | aegis/registry.py | Test |
| REQ-088 | The system shall support runtime overrides of graph configuration fields through launch payload parameters. | aegis/serve_dashboard.py, aegis/runner.py | Test |
| REQ-089 | The runner shall raise an exception if a preset does not define a valid `initial_state`. | aegis/runner.py, aegis/presets.yaml | Test |
| REQ-090 | The system shall record all tool execution outputs and errors in the final task log. | aegis/runner.py | Test |
| REQ-091 | The shell wrapper shall allow explicitly passing environment variables to the subprocess environment. | aegis/tools/wrappers/shell.py | Test |
| REQ-092 | The registry shall expose a function that returns a list of all registered tool names and metadata. | aegis/registry.py | Test |
| REQ-093 | The filesystem wrapper shall raise an error if batch operations include a path that does not exist. | aegis/tools/wrappers/wrapper_filesystem.py | Test |
| REQ-094 | The LLM wrapper shall return an error if the underlying model backend is unreachable or returns an error. | aegis/tools/wrappers/llm.py | Test |
| REQ-095 | The fuzzing wrapper shall raise an error if the provided shell command template lacks a substitution target. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-096 | The agent shall validate that each tool defines a unique name during registration. | aegis/registry.py | Test |
| REQ-097 | The fuzzing wrapper shall allow users to specify a maximum number of iterations per session. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-098 | The runner shall reject a graph configuration if it references an undefined node transition. | aegis/runner.py | Test |
| REQ-099 | The registry shall tag all tools with `safe_mode=True` by default unless explicitly overridden. | aegis/registry.py | Test |
| REQ-100 | The runner shall include a utility for rendering runtime output as both human-readable and machine-readable summaries. | aegis/runner.py | Test |
| REQ-101 | The dashboard endpoint shall return HTTP 400 for malformed input and include diagnostic error detail. | aegis/serve_dashboard.py | Test |
| REQ-102 | The fuzzing tool shall log and report every crash or unhandled exception triggered by a fuzzed command. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-103 | The registry shall enforce a minimum metadata contract for every tool, including `name`, `input_model`, and `tags`. | aegis/registry.py | Test |
| REQ-104 | The LLM wrapper shall support injecting context parameters into prompts when defined by the user. | aegis/tools/wrappers/llm.py | Test |
| REQ-105 | The filesystem primitive shall raise an error if it attempts to delete a directory outside the allowed sandbox. | aegis/tools/primitives/primitive_filesystem.py | Test |
| REQ-106 | The registry shall reject registration of tools with duplicate names and raise a descriptive exception. | aegis/registry.py | Test |
| REQ-107 | The runner shall log each graph transition, including source state, destination state, and selected tool. | aegis/runner.py | Test |
| REQ-108 | The agent shall support optional delay or wait steps between tool executions when defined in the graph. | aegis/runner.py, aegis/presets.yaml | Test |
| REQ-109 | The system shall include unit tests for each primitive and wrapper tool to validate baseline functionality. | aegis/tools/primitives/, aegis/tools/wrappers/ | Test |
| REQ-110 | The system shall return a distinct and descriptive error code for each class of failure (e.g., timeout, validation, execution). | aegis/runner.py, aegis/serve_dashboard.py | Test |
| REQ-111 | The registry shall allow introspection of tool metadata during runtime to support self-reflection by agents. | aegis/registry.py | Test |
| REQ-112 | The LLM wrapper shall redact prompt content from logs if marked as sensitive. | aegis/tools/wrappers/llm.py | Test |
| REQ-113 | The agent shall allow conditional branching based on tool output values during runtime. | aegis/runner.py, aegis/presets.yaml | Test |
| REQ-114 | The fuzz wrapper shall support saving and restoring a session seed for reproducible fuzzing runs. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-115 | The registry shall raise an error if any registered tool's input model is not a valid Pydantic BaseModel. | aegis/registry.py | Test |
| REQ-116 | The runner shall support execution profiles that modify default runtime behavior via profile selection. | aegis/runner.py, aegis/presets.yaml | Test |
| REQ-117 | The system shall reject attempts to register tools with reserved or duplicate category tags. | aegis/registry.py, aegis/tools/tool_metadata.yaml | Test |
| REQ-118 | The shell wrapper shall support running commands with elevated privileges only when explicitly configured. | aegis/tools/wrappers/shell.py | Test |
| REQ-119 | The system shall reject invalid `.env` configurations at startup and halt container initialization. | docker-compose.yml, .env | Test |
| REQ-120 | The browser snapshot comparison tool shall return a diff score between two DOM states. | aegis/tools/wrappers/browser/web_snapshot_compare.py | Test |
| REQ-121 | The system shall allow toggling between structured and plaintext log formats via environment config. | aegis/registry.py, .env | Test |
| REQ-122 | The agent shall emit a final status indicator in the report signifying SUCCESS, PARTIAL, or FAILURE. | aegis/runner.py | Test |
| REQ-123 | The registry shall reject tool registration if the tool’s declared category is not recognized. | aegis/registry.py | Test |
| REQ-124 | The dashboard shall expose a `/health` route that returns an HTTP 200 response if the server is operational. | aegis/serve_dashboard.py | Test |
| REQ-125 | The runner shall validate each node’s declared transitions for cycles or dead ends before execution begins. | aegis/runner.py | Test |
| REQ-126 | The system shall raise a configuration error if two tools share the same fully-qualified name and path. | aegis/registry.py | Test |
| REQ-127 | The fuzzing wrapper shall redact dangerous inputs from logs unless explicitly overridden by configuration. | aegis/tools/wrappers/fuzz.py | Test |
| REQ-128 | The browser interaction tool shall emit descriptive error messages when element selectors are invalid. | aegis/tools/wrappers/browser/web_interact.py | Test |
| REQ-129 | The registry shall support exporting the full tool index to a structured file such as JSON or YAML. | aegis/registry.py | Test |
| REQ-130 | The LLM wrapper shall fail gracefully and return a fallback message if model inference fails. | aegis/tools/wrappers/llm.py | Test |
| REQ-131 | The system shall support launching agent tasks using a locally stored manifest for virtualized hosts. | machines.yaml, aegis/runner.py | Test |
| REQ-132 | The registry shall log every successful tool registration event, including timestamp and category. | aegis/registry.py | Test |
| REQ-133 | The agent shall raise a fatal error if no valid tools are available in the registry at startup. | aegis/runner.py | Test |
| REQ-134 | The shell wrapper shall reject commands containing forbidden substrings unless allowlisted. | aegis/tools/wrappers/shell.py | Test |
| REQ-135 | The runner shall support emitting a summary file in JSON format after agent task completion. | aegis/runner.py | Test |