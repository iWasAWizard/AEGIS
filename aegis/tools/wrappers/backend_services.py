# aegis/tools/wrappers/backend_services.py
"""
Generic wrapper tools for interacting with backend services via the provider interface.

These tools allow AEGIS to leverage capabilities like speech synthesis or
transcription without being coupled to a specific backend implementation like BEND or OpenAI.
"""
from pathlib import Path

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class SpeechSynthesisInput(BaseModel):
    """Input for synthesizing speech using the configured backend."""
    text: str = Field(..., description="The text to be synthesized into speech.")
    output_path: str = Field(
        ..., description="The local file path to save the resulting audio file."
    )


class AudioTranscriptionInput(BaseModel):
    """Input for transcribing an audio file using the configured backend."""
    file_path: str = Field(
        ..., description="The local path to the audio file to be transcribed."
    )


@register_tool(
    name="synthesize_speech",
    input_model=SpeechSynthesisInput,
    description="Uses the configured backend to convert text into a spoken audio file.",
    tags=["backend", "tts", "audio", "integration"],
    category="integration",
    safe_mode=True,
)
async def synthesize_speech(input_data: SpeechSynthesisInput, provider: BackendProvider) -> str:
    """Sends text to the backend's TTS service and saves the returned audio."""
    logger.info(f"Synthesizing speech for text: '{input_data.text[:50]}...'")
    try:
        audio_bytes = await provider.get_speech(input_data.text)
        with open(input_data.output_path, "wb") as f:
            f.write(audio_bytes)
        return f"Successfully synthesized speech and saved to '{input_data.output_path}'."
    except NotImplementedError:
        raise ToolExecutionError(f"The configured backend does not support speech synthesis.")
    except Exception as e:
        raise ToolExecutionError(f"Failed to synthesize speech: {e}")


@register_tool(
    name="transcribe_audio",
    input_model=AudioTranscriptionInput,
    description="Uses the configured backend to transcribe an audio file into text.",
    tags=["backend", "stt", "audio", "integration"],
    category="integration",
    safe_mode=True,
)
async def transcribe_audio(input_data: AudioTranscriptionInput, provider: BackendProvider) -> str:
    """Sends an audio file to the backend's STT service and returns the transcription."""
    logger.info(f"Transcribing audio file: {input_data.file_path}")
    audio_path = Path(input_data.file_path)

    if not audio_path.is_file():
        raise ToolExecutionError(f"Audio file not found at: {input_data.file_path}")

    try:
        with audio_path.open("rb") as f:
            audio_bytes = f.read()
        transcription = await provider.get_transcription(audio_bytes)
        return transcription
    except NotImplementedError:
        raise ToolExecutionError(f"The configured backend does not support audio transcription.")
    except Exception as e:
        raise ToolExecutionError(f"Failed to transcribe audio: {e}")