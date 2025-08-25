# Developer Guide: Creating a New Tool

This guide provides a complete walkthrough for adding a new tool to the AEGIS framework. Adding new tools is the primary way to extend an agent's capabilities, and the framework is designed to make this process as simple and robust as possible.

We will create a practical example tool: `get_public_ip`, which will find the host's public IP address by calling an external API.

## The Philosophy of a Good Tool

Before we write any code, it's important to understand what makes a good tool in an agentic system.

-   **Do One Thing Well:** A tool should have a single, clear responsibility. Instead of a generic `network_manager` tool, create specific tools like `check_port_status`, `ping_host`, and `resolve_dns`. This makes the tool easier for the LLM to choose correctly.
-   **Be Self-Contained:** A tool should rely on a low-level `Executor` to do its work. It shouldn't contain complex connection logic itself. This makes your tool clean and easy to test.
-   **Have a Great Description:** The `description` field in the `@register_tool` decorator is the most important part of your tool. It's the *only* thing the agent's LLM planner sees. A clear, concise description is critical for the agent to understand when and how to use your tool.
-   **Use a Strict Input Schema:** A well-defined Pydantic `input_model` is your primary safety mechanism. It ensures the agent can't call your tool with malformed or unexpected arguments.

## Step 1: Scaffold the Tool File

AEGIS comes with a command-line utility to create a boilerplate file for your new tool. This is the best way to start, as it sets up the file structure and all the required components.

Run the following command from the AEGIS repository root:

```bash
python -m aegis.cli new-tool
```

The CLI will interactively ask you for the details of your new tool. For our example, you would answer like this:

-   **Tool Name:** `get_public_ip`
-   **Description:** `Finds the public IP address of the host by querying an external API.`
-   **Category:** `network`
-   **Is this tool safe?** `Yes` (It's a read-only operation).

This will generate a new file in the `plugins/` directory named `get_public_ip.py`. The `plugins/` directory is automatically scanned by AEGIS at startup, so any valid tool you place here will be registered and made available to the agent.

## Step 2: Define the Input Schema

Open the newly created file, `plugins/get_public_ip.py`. The first thing to do is define the tool's input model. This is a Pydantic `BaseModel` that defines the arguments your tool accepts.

Our tool needs to know which API to query. We'll add a `service_url` argument and give it a sensible default, but we'll allow the agent to override it if it needs to.

```python
# plugins/get_public_ip.py
from pydantic import BaseModel, Field

# ... (other imports will go here) ...

class GetPublicIpInput(BaseModel):
    """Input model for the get_public_ip tool.

    The docstring here is for developers. The 'description' in the Field
    is what the agent's LLM will see.

    :ivar service_url: The URL of the IP lookup service to use.
    :vartype service_url: str
    """
    service_url: str = Field(
        default="https://api.ipify.org",
        description="The URL of the API service to query for the public IP address."
    )```

By using a Pydantic model, we get free validation, type safety, and clear documentation. The agent's planner *must* provide a valid string for this argument, or the tool will fail with a clear validation error before it even runs.

## Step 3: Implement the Tool's Logic

Now, let's write the main function. This is where we will use one of AEGIS's built-in, robust `Executors` to do the heavy lifting.

1.  **Import the necessary components:** We need the `HttpExecutor` to make web requests and the `ToolExecutionError` exception to handle failures gracefully.
2.  **Instantiate the Executor:** Inside the function, we create an instance of the `HttpExecutor`.
3.  **Call the Executor:** We use the executor's `request` method to make a `GET` request to the URL provided in our input model.
4.  **Handle Errors:** We wrap the logic in a `try...except` block. If anything goes wrong, we catch the exception, log it, and re-raise it as a `ToolExecutionError`. This ensures the agent gets a clear, standardized error message.
5.  **Return the Result:** We return the text from the API response.

Here is the complete, final code for the tool file:

```python
# plugins/get_public_ip.py
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.executors.http import HttpExecutor
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class GetPublicIpInput(BaseModel):
    """Input model for the get_public_ip tool.

    :ivar service_url: The URL of the IP lookup service to use.
    :vartype service_url: str
    """
    service_url: str = Field(
        default="https://api.ipify.org",
        description="The URL of the API service to query for the public IP address."
    )


@register_tool(
    name="get_public_ip",
    input_model=GetPublicIpInput,
    description="Finds the public IP address of the host by querying an external API.",
    category="network",
    tags=["custom", "network", "ip"],
    safe_mode=True
)
def get_public_ip(input_data: GetPublicIpInput) -> str:
    """Finds the public IP address of the host by querying an external API.

    :param input_data: The validated input data for the tool.
    :type input_data: GetPublicIpInput
    :return: A string containing the public IP address.
    :rtype: str
    :raises ToolExecutionError: If the web request fails.
    """
    logger.info(f"Executing tool: get_public_ip with service '{input_data.service_url}'")

    try:
        # 1. Instantiate the Executor
        http_executor = HttpExecutor()

        # 2. Call the Executor
        response = http_executor.request(
            method="GET",
            url=input_data.service_url
        )

        # 3. Process and Return the Result
        # The API returns the IP as plain text in the response body.
        public_ip = response.text.strip()
        logger.info(f"Successfully found public IP: {public_ip}")
        return public_ip

    except Exception as e:
        # 4. Handle Errors
        logger.exception("get_public_ip tool failed during execution.")
        # Re-raise as a ToolExecutionError so the agent gets a clean error message.
        raise ToolExecutionError(f"Failed to get public IP: {e}")
```

## Step 4: Validate and Test Your New Tool

You don't need to run the full agent to make sure your tool is working.

1.  **Validate the File:**
    Use the CLI to check for syntax errors and correct registration.
    ```bash
    python -m aegis.cli validate-tool plugins/get_public_ip.py
    ```
    You should see a `Validation Successful!` message.

2.  **Write a Simple Unit Test:**
    Create a new file in `aegis/tests/tools/plugins/` (you may need to create the `plugins` folder) named `test_get_public_ip.py`. Here's a simple test using `pytest` and mocking.

    ```python
    # aegis/tests/tools/plugins/test_get_public_ip.py
    from unittest.mock import MagicMock
    import pytest
    from plugins.get_public_ip import get_public_ip, GetPublicIpInput

    @pytest.fixture
    def mock_http_executor(monkeypatch):
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "123.45.67.89"
        mock_instance.request.return_value = mock_response

        mock_class = MagicMock(return_value=mock_instance)
        monkeypatch.setattr("plugins.get_public_ip.HttpExecutor", mock_class)
        return mock_instance

    def test_get_public_ip_success(mock_http_executor):
        input_data = GetPublicIpInput()
        result = get_public_ip(input_data)
        assert result == "123.45.67.89"
        mock_http_executor.request.assert_called_once_with(method="GET", url="https://api.ipify.org")
    ```
    You can run this test with `pytest aegis/tests/tools/plugins/test_get_public_ip.py`.

## Step 5: Use Your Tool

Now, your tool is ready to be used by the agent.

1.  **Start AEGIS:**
    ```bash
    docker compose up --build
    ```

2.  **Verify Registration in the UI:**
    -   Go to `http://localhost:8000` and click the **"Tools"** tab.
    -   You should see your new tool, `get_public_ip`, in the inventory.

3.  **Give the Agent a Task:**
    -   Go to the **"Launch"** tab.
    -   Give the agent a prompt that requires your new tool:
        > `What is my public IP address?`
    -   Launch the task.

The agent will see your new tool in its list of capabilities and correctly choose it to solve the task.

---

That's it! You have successfully extended the AEGIS framework with a new, robust, and reusable capability. You can follow this same pattern to add any tool you need.