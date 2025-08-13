# aegis/providers/vision_provider.py
"""
A provider for interacting with a vision-enabled language model (VLM).
"""
import base64
import httpx
from aegis.exceptions import ToolExecutionError
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class VisionProvider:
    """Provider for interacting with an Ollama-hosted vision model like LLaVA."""

    def __init__(self, config):
        self.config = config
        self.vision_model_name = "llava:7b"  # The model BEND is configured to run

    async def describe_image(self, prompt: str, image_bytes: bytes) -> str:
        """
        Sends a prompt and an image to the VLM and returns a description.
        """
        if not self.config.vision_url:
            raise ToolExecutionError(
                "Vision service URL is not configured in backends.yaml."
            )

        url = f"{self.config.vision_url}/api/generate"
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self.vision_model_name,
            "prompt": prompt,
            "images": [encoded_image],
            "stream": False,
        }

        logger.info(f"Sending image to Vision model at {self.config.vision_url}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=120.0)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "[No description in VLM response]")
        except httpx.RequestError as e:
            raise ToolExecutionError(f"Vision model request failed: {e}") from e
