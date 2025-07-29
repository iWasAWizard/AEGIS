Of course. Let's tackle the next guide for developers: **Adding a New Backend Provider**.

This is a more advanced guide, but it's essential for the framework's long-term health and adaptability. It explains the core "Provider" pattern and gives a clear, step-by-step process for integrating AEGIS with a new, unsupported AI backend.

---

# Developer Guide: Adding a New Backend Provider

One of the core design principles of AEGIS is that it is **backend-agnostic**. The agent's reasoning logic is completely decoupled from the specific AI service that provides the intelligence. This is achieved through the **Provider** architectural pattern.

This guide will walk you through the process of adding a new, custom `BackendProvider` to AEGIS. This will allow you to connect the framework to any AI backend, whether it's a new open-source model server or a commercial API that isn't supported out-of-the-box.

As our example, we will create a fictional `ExampleComProvider` for a hypothetical AI service called "Example.com".

## The Provider Contract

The foundation of the provider system is the abstract base class located at `aegis/providers/base.py`. This `BackendProvider` class defines the "contract"—a set of methods that every concrete provider *must* implement.

The key methods are:
-   **`get_completion(...)`**: Takes a list of messages and returns a string from the LLM.
-   **`get_speech(...)`**: Takes text and returns audio bytes.
-   **`get_transcription(...)`**: Takes audio bytes and returns text.
-   *(...and others for RAG, etc.)*

If your backend doesn't support a specific capability (like speech synthesis), you should raise a `NotImplementedError` in that method.

## Step 1: Create the Configuration Schema

The first step is to define how a user will configure your new provider. This is done by creating a Pydantic model in `aegis/schemas/backend.py`.

1.  **Open `aegis/schemas/backend.py`**.
2.  **Add your new configuration model.** It should inherit from `BaseBackendConfig`. Define all the fields your provider will need, such as the API URL and any necessary LLM parameters.

```python
# aegis/schemas/backend.py
# ... (other imports) ...

class ExampleComBackendConfig(BaseBackendConfig):
    """Configuration specific to the fictional Example.com API."""

    type: Literal["example_com"] = "example_com"
    llm_url: str = Field(
        ..., description="The full URL to the Example.com /completion endpoint."
    )
    api_key: str = Field(..., description="The API key for the Example.com service.")
    model: str = Field("example-model-v1", description="The model name to use.")
    temperature: float = Field(0.5)
```

## Step 2: Implement the Provider Class

Next, you will create the Python class that contains the logic for interacting with the backend's API.

1.  **Create a New File:**
    Create a new file in the `aegis/providers/` directory. For our example, this would be `aegis/providers/example_com_provider.py`.

2.  **Implement the Class:**
    -   The class must inherit from `BackendProvider`.
    -   The `__init__` method should accept the Pydantic config model you created in Step 1.
    -   You must implement the `get_completion` method. This is where you will make the actual API call to your backend.
    -   For any unsupported methods, raise `NotImplementedError`.

```python
# aegis/providers/example_com_provider.py
import aiohttp
from typing import List, Dict, Any, Optional

from aegis.exceptions import PlannerError
from aegis.providers.base import BackendProvider
from aegis.schemas.backend import ExampleComBackendConfig # Your new schema
from aegis.schemas.runtime import RuntimeExecutionConfig

class ExampleComProvider(BackendProvider):
    """Provider for the fictional Example.com AI service."""

    def __init__(self, config: ExampleComBackendConfig):
        self.config = config

    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
        # 1. Construct the payload for the specific API
        payload = {
            "model": self.config.model,
            "prompt": messages[-1]['content'], # Example: maybe it only takes the last user prompt
            "temp": self.config.temperature,
            # ... other parameters
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}"
        }

        # 2. Make the API call using aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.config.llm_url, json=payload, headers=headers) as response:
                    response.raise_for_status() # Raise an exception for bad status codes
                    result = await response.json()

                    # 3. Parse the response and return the text
                    # This part is highly specific to the API's response format
                    return result["data"]["choices"][0]["text"]

        except aiohttp.ClientError as e:
            # 4. Handle errors gracefully
            raise PlannerError(f"Network error while querying Example.com: {e}") from e

    # 5. Implement other methods as needed, or raise NotImplementedError
    async def get_speech(self, text: str) -> bytes:
        raise NotImplementedError("Example.com does not support speech synthesis.")

    async def get_transcription(self, audio_bytes: bytes) -> str:
        raise NotImplementedError("Example.com does not support transcription.")

    # ... (implement other methods similarly) ...
```

## Step 3: Wire Up the New Provider

The final step is to teach AEGIS's factory functions how to recognize and instantiate your new provider.

1.  **Open `aegis/utils/backend_loader.py`:**
    -   Import your new config schema (`ExampleComBackendConfig`).
    -   Add an `elif` block to the `get_backend_config` function to handle the new `type`.

    ```python
    # aegis/utils/backend_loader.py
    # ...
    from aegis.schemas.backend import (
        KoboldcppBackendConfig,
        OllamaBackendConfig,
        OpenAIBackendConfig,
        VllmBackendConfig,
        ExampleComBackendConfig, # Add this
        BaseBackendConfig,
    )
    # ...

    def get_backend_config(profile_name: str) -> Any:
        # ... (existing code) ...
        try:
            backend_type = backend_config_raw.get("type")
            if backend_type == "koboldcpp":
                return KoboldcppBackendConfig(**backend_config_raw)
            elif backend_type == "ollama":
                return OllamaBackendConfig(**backend_config_raw)
            elif backend_type == "openai":
                return OpenAIBackendConfig(**backend_config_raw)
            elif backend_type == "vllm":
                return VllmBackendConfig(**backend_config_raw)
            elif backend_type == "example_com": # Add this block
                return ExampleComBackendConfig(**backend_config_raw)
            else:
                raise ConfigurationError(f"Unknown backend type '{backend_type}'...")
        # ... (existing code) ...
    ```

2.  **Open `aegis/utils/llm_query.py`:** (Note: This file is now primarily for provider-aware tools)
    -   Import your new provider class (`ExampleComProvider`).
    -   Add an `elif` block to the `get_provider_for_profile` factory function.

    ```python
    # aegis/utils/llm_query.py
    # ...
    from aegis.providers.koboldcpp_provider import KoboldcppProvider
    from aegis.providers.openai_provider import OpenAIProvider
    from aegis.providers.vllm_provider import VllmProvider
    from aegis.providers.example_com_provider import ExampleComProvider # Add this
    # ...

    def get_provider_for_profile(profile_name: str) -> BackendProvider:
        backend_config = get_backend_config(profile_name)

        if backend_config.type == "koboldcpp":
            return KoboldcppProvider(config=backend_config)
        elif backend_config.type == "openai":
            return OpenAIProvider(config=backend_config)
        elif backend_config.type == "vllm":
            return VllmProvider(config=backend_config)
        elif backend_config.type == "example_com": # Add this block
            return ExampleComProvider(config=backend_config)
        else:
            raise ConfigurationError(f"Unsupported backend provider type: '{backend_config.type}'")
    ```

## Step 4: Configure and Use Your New Provider

Your new provider is now fully integrated. To use it:

1.  **Add a Profile to `backends.yaml`:**
    ```yaml
    # aegis/backends.yaml
    - profile_name: example_com_default
      type: example_com
      llm_url: "https://api.example.com/v1/completion"
      api_key: ${EXAMPLE_COM_API_KEY}
      model: "example-model-v1"
    ```

2.  **Add the Secret to `.env`:**
    ```env
    # AEGIS/.env
    EXAMPLE_COM_API_KEY=ec-xxxxxxxxxxxx
    ```

3.  **Use it:**
    You can now select `"example_com_default"` as the "Backend Profile" in the AEGIS UI or in your task files. The framework will automatically load your new provider and use it to power the agent's reasoning.

---

By following this pattern, you can connect AEGIS to virtually any AI backend, ensuring the framework remains flexible and future-proof.