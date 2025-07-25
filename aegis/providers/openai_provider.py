# aegis/providers/openai_provider.py
"""
A concrete implementation of the BackendProvider for OpenAI's API.
"""
from typing import List, Dict, Any, Optional, Type
import io

import openai
from pydantic import BaseModel

from aegis.exceptions import PlannerError, ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.schemas.backend import OpenAIBackendConfig
from aegis.schemas.runtime import RuntimeExecutionConfig
from aegis.utils.logger import setup_logger

try:
    import instructor
except ImportError:
    instructor = None


logger = setup_logger(__name__)


class OpenAIProvider(BackendProvider):
    """
    Provider for interacting with the official OpenAI Chat Completions API.
    """

    def __init__(self, config: OpenAIBackendConfig):
        self.config = config
        self.client = openai.AsyncOpenAI(api_key=self.config.api_key)
        if instructor:
            self.structured_client = instructor.patch(
                openai.AsyncOpenAI(api_key=self.config.api_key)
            )
        else:
            self.structured_client = None

    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
        """
        Gets a completion from the OpenAI API.
        """
        logger.info(f"Sending prompt to OpenAI backend (model: {self.config.model})")

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,  # type: ignore
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens_to_generate,
                top_p=self.config.top_p,
                timeout=runtime_config.llm_planning_timeout,
            )
            content = response.choices[0].message.content
            return content or "[No content in OpenAI response]"
        except openai.APIError as e:
            logger.exception(f"OpenAI API error: {e}")
            raise PlannerError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.exception("An unexpected error occurred while querying OpenAI.")
            raise PlannerError(f"Unexpected error during OpenAI query: {e}")

    async def get_structured_completion(
        self, system_prompt: str, user_prompt: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        if not self.structured_client:
            raise ToolExecutionError(
                "The 'instructor' library is required for structured completion."
            )
        response = await self.structured_client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_model=response_model,
        )
        return response

    async def get_speech(self, text: str) -> bytes:
        """Generates speech using OpenAI's TTS-1 model."""
        logger.info(
            f"Requesting speech from OpenAI TTS (model: {self.config.tts_model})"
        )
        try:
            response = await self.client.audio.speech.create(
                model=self.config.tts_model,
                voice=self.config.tts_voice,  # type: ignore
                input=text,
            )
            return response.read()
        except openai.APIError as e:
            raise ToolExecutionError(f"OpenAI speech synthesis failed: {e}") from e

    async def get_transcription(self, audio_bytes: bytes) -> str:
        """Transcribes audio using OpenAI's Whisper-1 model."""
        logger.info(
            f"Requesting transcription from OpenAI Whisper (model: {self.config.stt_model})"
        )
        try:
            # The OpenAI library expects a file-like object, so we wrap the bytes.
            # We also need to give it a name with a valid extension.
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"

            transcript = await self.client.audio.transcriptions.create(
                model=self.config.stt_model,
                file=audio_file,
            )
            return transcript.text
        except openai.APIError as e:
            raise ToolExecutionError(f"OpenAI audio transcription failed: {e}") from e

    async def ingest_document(
        self, file_path: str, source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError("OpenAIProvider does not support document ingestion.")

    async def retrieve_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "OpenAIProvider does not support knowledge retrieval."
        )
