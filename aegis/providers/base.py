# aegis/providers/base.py
"""
Defines the abstract base class for all backend providers.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type

from pydantic import BaseModel
from aegis.schemas.runtime import RuntimeExecutionConfig


class BackendProvider(ABC):
    """
    An abstract base class that defines the standard interface for a backend
    intelligence provider. All concrete provider implementations (e.g., for BEND,
    OpenAI) must inherit from this class and implement its methods.
    """

    @abstractmethod
    async def get_completion(
        self, messages: List[Dict[str, Any]], runtime_config: RuntimeExecutionConfig
    ) -> str:
        """
        Gets a completion from the backend's language model.

        :param messages: A list of message dictionaries, following the standard {'role': ..., 'content': ...} format.
        :param runtime_config: The runtime configuration for this specific request.
        :return: The string content of the model's response.
        """
        pass

    @abstractmethod
    async def get_structured_completion(
        self,
        messages: List[Dict[str, Any]],
        response_model: Type[BaseModel],
        runtime_config: RuntimeExecutionConfig,
    ) -> BaseModel:
        """
        Gets a structured completion from the backend's language model.
        """
        pass

    @abstractmethod
    async def get_speech(self, text: str) -> bytes:
        """
        Generates speech audio from text.

        :param text: The text to synthesize.
        :return: The raw audio data as bytes.
        """
        pass

    @abstractmethod
    async def get_transcription(self, audio_bytes: bytes) -> str:
        """
        Transcribes audio data to text.

        :param audio_bytes: The raw audio data as bytes.
        :return: The transcribed text.
        """
        pass

    @abstractmethod
    async def ingest_document(
        self, file_path: str, source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingests a document into the backend's RAG system.

        :param file_path: The local path to the file to ingest.
        :param source_name: An optional name to store as the source of the document.
        :return: A dictionary containing the response from the ingestion service.
        """
        pass

    @abstractmethod
    async def retrieve_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves knowledge from the backend's RAG system.

        :param query: The query to search for.
        :param top_k: The number of results to return.
        :return: A list of dictionaries, where each dictionary is a retrieved chunk.
        """
        pass
