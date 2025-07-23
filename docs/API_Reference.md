# AEGIS API Reference

The AEGIS API provides a set of RESTful endpoints for launching and managing autonomous agent tasks. It is served by a FastAPI application and uses Pydantic for strict data validation and serialization.

The base URL for all endpoints described below is `http://localhost:8000/api`.

---

## **Primary Endpoint**

### `POST /launch`

This is the main endpoint for initiating a new agent task. It accepts a comprehensive JSON payload that defines the agent's goal and its complete configuration for the run. The request is synchronous and will hold the connection open until the agent has finished its task, returning the final result.

#### Request Body

The request body must be a JSON object conforming to the `LaunchRequest` schema.

-   **`task`** `(object)`: **Required.** Contains the core details of the task.
    -   `prompt` `(string)`: **Required.** The high-level, natural language goal for the agent.
    -   `task_id` `(string, optional)`: A unique ID for the task. If not provided, a UUID will be generated.
-   **`config`** `(string or object)`: **Required.** Defines the agent's workflow.
    -   If a `string`, it must be the ID of a preset from the `presets/` directory (e.g., `"default"`, `"verified_flow"`).
    -   If an `object`, it must be a complete agent configuration that conforms to the `AgentConfig` schema.
-   **`execution`** `(object, optional)`: An object containing runtime overrides for this specific task. Any fields provided here will take precedence over the defaults in the chosen preset or `config.yaml`.
    -   `backend_profile` `(string)`: The name of the backend profile from `backends.yaml` to use.
    -   `llm_model_name` `(string)`: The key of the model from `models.yaml` to use.
    -   `iterations` `(integer)`: The maximum number of steps the agent can take.
    -   `safe_mode` `(boolean)`: Whether to block unsafe tools for this run.
    -   `tool_allowlist` `(array of strings)`: A list of tool names to restrict the agent to for this run.
    -   *(...and other fields from the `RuntimeExecutionConfig` schema)*

#### Example Request

```json
{
  "task": {
    "prompt": "Create a file named 'report.txt' and write the current date into it."
  },
  "config": "verified_flow",
  "execution": {
    "backend_profile": "vllm_local",
    "llm_model_name": "llama3",
    "iterations": 10
  }
}
```

#### Responses

-   **`200 OK`**: The task completed successfully (or was successfully paused). The response body will be a `LaunchResponse` object.

    -   **`task_id`** `(string)`: The unique ID for the completed task.
    -   **`summary`** `(string)`: A human-readable, Markdown-formatted summary of the entire task.
    -   **`status`** `(string)`: The final status. Will be `"COMPLETED"` for a normal run, or `"PAUSED"` if the agent is waiting for human input.
    -   **`history`** `(array of objects)`: A step-by-step log of the agent's execution. Each object in the array represents one step and contains:
        -   `thought` `(string)`: The agent's reasoning for the step.
        -   `tool_name` `(string)`: The name of the tool that was executed.
        -   `tool_args` `(object)`: The arguments passed to the tool.
        -   `tool_output` `(string)`: The stringified result from the tool.

-   **`400 Bad Request`**: The request payload failed validation (e.g., missing required fields, invalid preset name). The response detail will contain information about the error.
-   **`500 Internal Server Error`**: The agent encountered a critical, unrecoverable error during execution (e.g., a `PlannerError` or a `ToolExecutionError`). The response detail will contain the error message.

---

## **Human-in-the-Loop Endpoint**

### `POST /resume`

This endpoint is used to continue a task that has been paused by the agent using the `ask_human_for_input` tool.

#### Request Body

-   **`task_id`** `(string)`: **Required.** The ID of the paused task you wish to resume.
-   **`human_feedback`** `(string)`: **Required.** The text you want to provide to the agent as its new "observation."

#### Example Request

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "human_feedback": "Yes, you have my permission to proceed with deleting the file."
}
```

#### Responses

-   **`200 OK`**: The task was successfully resumed and has now completed. The response body will be a `LaunchResponse` object, identical in structure to the `/launch` endpoint's success response.
-   **`404 Not Found`**: The specified `task_id` does not correspond to a currently paused task.

---

## **Informational Endpoints**

These are `GET` endpoints used by the UI to populate its various panels.

-   **`GET /inventory`**: Returns a list of all available tools and their metadata, including their input schemas.
-   **`GET /presets`**: Returns a list of all available agent configuration presets.
-   **`GET /backends`**: Returns a list of all available backend profiles from `backends.yaml`.
-   **`GET /models`**: Returns the list of all models from the synchronized `models.yaml`.
-   **`GET /artifacts`**: Returns a list of all completed tasks that have generated reports or artifacts.
-   **`GET /artifacts/{task_id}/summary`**: Returns the raw Markdown summary for a specific task.
-   **`GET /artifacts/{task_id}/provenance`**: Returns the raw JSON provenance report for a specific task.

## **WebSocket Endpoint**

### `GET /ws/logs`

Establishes a WebSocket connection for receiving real-time logs from the agent as it executes a task.

-   **Protocol:** `ws` or `wss`
-   **Messages:** The server pushes plain text log messages to the client as they are generated. The connection is one-way (server-to-client).