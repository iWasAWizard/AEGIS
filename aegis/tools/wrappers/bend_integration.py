# aegis/tools/wrappers/bend_integration.py
"""
Wrapper tools for integrating AEGIS with a BEND (Backend Enhanced Neural Dispatch) stack.

These tools act as clients for the services provided by BEND, allowing AEGIS
to leverage BEND's capabilities for speech synthesis, transcription, and
retrieval-augmented generation from external documents.
"""
import os
from pathlib import Path

import requests
from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)

# Load BEND service URLs from environment variables with defaults
BEND_VOICE_PROXY_URL = os.getenv("BEND_VOICE_PROXY_URL", "http://voiceproxy:8001")
BEND_RETRIEVER_URL = os.getenv("BEND_RETRIEVER_URL", "http://retriever:8000")
BEND_API_KEY = os.getenv("BEND_API_KEY")


def _get_bend_headers() -> dict:
    """Constructs the headers for BEND API requests, including the API key if present."""
    headers = {"Content-Type": "application/json"}
    if BEND_API_KEY:
        headers["X-API-Key"] = BEND_API_KEY
    return headers


# --- Input Models ---


class BendSpeakInput(BaseModel):
    """Input for synthesizing speech using the BEND voice proxy."""

    text: str = Field(..., description="The text to be synthesized into speech.")
    output_path: str = Field(
        ..., description="The local file path to save the resulting .wav audio file."
    )


class BendTranscribeInput(BaseModel):
    """Input for transcribing an audio file using the BEND voice proxy."""

    file_path: str = Field(
        ..., description="The local path to the audio file to be transcribed."
    )


class BendIngestInput(BaseModel):
    """Input for ingesting a document into BEND's RAG system."""

    file_path: str = Field(
        ..., description="The local path to the document (.txt, .md, .pdf) to ingest."
    )


class BendRetrieveInput(BaseModel):
    """Input for querying BEND's document knowledge base."""

    query: str = Field(
        ..., description="The natural language query to search for in the documents."
    )
    top_k: int = Field(
        3, ge=1, le=20, description="The number of relevant chunks to retrieve."
    )


# --- Tools ---


@register_tool(
    name="bend_synthesize_speech",
    input_model=BendSpeakInput,
    description="Uses the BEND stack to convert text into a spoken .wav audio file.",
    tags=["bend", "tts", "audio", "integration"],
    category="integration",
    safe_mode=True,
)
def bend_synthesize_speech(input_data: BendSpeakInput) -> str:
    """Sends text to BEND's TTS service and saves the returned audio."""
    logger.info(f"Synthesizing speech for text: '{input_data.text[:50]}...'")
    url = f"{BEND_VOICE_PROXY_URL}/speak"
    try:
        response = requests.post(
            url, json={"text": input_data.text}, headers=_get_bend_headers(), timeout=60
        )
        response.raise_for_status()

        with open(input_data.output_path, "wb") as f:
            f.write(response.content)

        return (
            f"Successfully synthesized speech and saved to '{input_data.output_path}'."
        )
    except requests.RequestException as e:
        raise ToolExecutionError(f"Failed to connect to BEND voice proxy: {e}")
    except IOError as e:
        raise ToolExecutionError(
            f"Failed to write audio file to '{input_data.output_path}': {e}"
        )


@register_tool(
    name="bend_transcribe_audio",
    input_model=BendTranscribeInput,
    description="Uses the BEND stack to transcribe an audio file into text.",
    tags=["bend", "stt", "audio", "integration"],
    category="integration",
    safe_mode=True,
)
def bend_transcribe_audio(input_data: BendTranscribeInput) -> str:
    """Sends an audio file to BEND's STT service and returns the transcription."""
    logger.info(f"Transcribing audio file: {input_data.file_path}")
    url = f"{BEND_VOICE_PROXY_URL}/transcribe"
    audio_path = Path(input_data.file_path)

    if not audio_path.is_file():
        raise ToolExecutionError(f"Audio file not found at: {input_data.file_path}")

    try:
        with audio_path.open("rb") as f:
            files = {"file": (audio_path.name, f)}
            # Remove content-type for multipart uploads, requests will set it.
            headers = {
                k: v for k, v in _get_bend_headers().items() if k != "Content-Type"
            }
            response = requests.post(url, files=files, headers=headers, timeout=120)

        response.raise_for_status()
        return response.json().get("text", "[No text in transcription response]")
    except requests.RequestException as e:
        raise ToolExecutionError(f"Failed to connect to BEND voice proxy: {e}")


@register_tool(
    name="bend_ingest_document",
    input_model=BendIngestInput,
    description="Uploads a document to the BEND stack for RAG indexing.",
    tags=["bend", "rag", "document", "ingest", "integration"],
    category="integration",
    safe_mode=True,
)
def bend_ingest_document(input_data: BendIngestInput) -> str:
    """Sends a document file to BEND's RAG retriever service."""
    logger.info(f"Ingesting document into BEND: {input_data.file_path}")
    url = f"{BEND_RETRIEVER_URL}/ingest"
    doc_path = Path(input_data.file_path)

    if not doc_path.is_file():
        raise ToolExecutionError(f"Document not found at: {input_data.file_path}")

    try:
        with doc_path.open("rb") as f:
            files = {"file": (doc_path.name, f)}
            headers = {
                k: v for k, v in _get_bend_headers().items() if k != "Content-Type"
            }
            response = requests.post(url, files=files, headers=headers, timeout=180)

        response.raise_for_status()
        return response.json().get("message", "Ingestion status unknown.")
    except requests.RequestException as e:
        raise ToolExecutionError(f"Failed to connect to BEND retriever service: {e}")


@register_tool(
    name="bend_retrieve_knowledge",
    input_model=BendRetrieveInput,
    description="Queries the BEND stack's document store (RAG) to get context.",
    tags=["bend", "rag", "document", "retrieve", "integration"],
    category="integration",
    safe_mode=True,
)
def bend_retrieve_knowledge(input_data: BendRetrieveInput) -> list:
    """Sends a query to BEND's RAG retriever and returns the results."""
    logger.info(f"Retrieving knowledge from BEND with query: '{input_data.query}'")
    url = f"{BEND_RETRIEVER_URL}/retrieve"
    payload = {"query": input_data.query, "top_k": input_data.top_k}

    try:
        response = requests.post(
            url, json=payload, headers=_get_bend_headers(), timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise ToolExecutionError(f"Failed to connect to BEND retriever service: {e}")
