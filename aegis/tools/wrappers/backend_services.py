# aegis/tools/wrappers/backend_services.py
"""
Wrapper tools for interacting directly with configured backend services.

These tools are "provider-aware," meaning they accept the agent's current
TaskState to access the configured BackendProvider instance. This allows them
to leverage the backend's native capabilities, such as speech synthesis or
transcription, in a backend-agnostic way.
"""
from pathlib import Path

from pydantic import BaseModel, Field

from aegis.agents.task_state import TaskState
from aegis.exceptions import ToolExecutionError
from aegis.providers.base import BackendProvider
from aegis.registry import register_tool
from aegis.utils.artifact_manager import save_artifact
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


# --- Input Models ---


class SynthesizeSpeechInput(BaseModel):
    """Input for synthesizing speech from text.

    :ivar text: The text to convert into speech.
    :vartype text: str
    :ivar output_filename: The local filename for the generated audio (e.g., 'response.wav').
    :vartype output_filename: str
    """

    text: str = Field(..., description="The text to convert into speech.")
    output_filename: str = Field(
        ...,
        description="The local filename for the generated audio (e.g., 'response.wav').",
    )


class TranscribeAudioInput(BaseModel):
    """Input for transcribing an audio file to text.

    :ivar audio_file_path: The local path to the audio file to transcribe.
    :vartype audio_file_path: str
    """

    audio_file_path: str = Field(
        ..., description="The local path to the audio file to transcribe."
    )


# --- Tools ---


@register_tool(
    name="synthesize_speech",
    input_model=SynthesizeSpeechInput,
    description="Generates speech from text using the configured backend's TTS service and saves it as an artifact.",
    category="multimodal",
    tags=["tts", "speech", "audio", "backend", "provider-aware"],
    safe_mode=True,
    purpose="Convert text into spoken audio.",
)
async def synthesize_speech(
    input_data: SynthesizeSpeechInput, state: TaskState, provider: BackendProvider
) -> str:
    """
    Uses the active backend provider to perform text-to-speech and saves the
    resulting audio file as a task artifact.

    :param input_data: The text to synthesize and the output filename.
    :type input_data: SynthesizeSpeechInput
    :param state: The current agent task state.
    :type state: TaskState
    :param provider: The active backend provider instance.
    :type provider: BackendProvider
    :return: A message indicating the path to the saved audio file.
    :rtype: str
    """
    logger.info(f"Synthesizing speech for text: '{input_data.text[:50]}...'")
    try:
        audio_bytes = await provider.get_speech(input_data.text)

        # Save the raw bytes to a temporary path first
        temp_path = Path(f"/tmp/{input_data.output_filename}")
        temp_path.write_bytes(audio_bytes)

        # Use the artifact manager to save it permanently with standardized naming
        artifact_path = save_artifact(temp_path, state.task_id, "synthesize_speech")

        # Clean up temp file
        temp_path.unlink()

        return (
            f"Speech synthesized successfully. Audio saved to artifact: {artifact_path}"
        )
    except NotImplementedError:
        raise ToolExecutionError(
            f"The current backend '{state.runtime.backend_profile}' does not support speech synthesis."
        )
    except Exception as e:
        logger.exception("Speech synthesis tool failed.")
        raise ToolExecutionError(f"Speech synthesis failed: {e}")


@register_tool(
    name="transcribe_audio",
    input_model=TranscribeAudioInput,
    description="Transcribes an audio file to text using the configured backend's STT service.",
    category="multimodal",
    tags=["stt", "speech", "audio", "backend", "provider-aware"],
    safe_mode=True,
    purpose="Convert spoken audio into text.",
)
async def transcribe_audio(
    input_data: TranscribeAudioInput, state: TaskState, provider: BackendProvider
) -> str:
    """
    Uses the active backend provider to perform speech-to-text on a local audio file.

    :param input_data: The path to the audio file to transcribe.
    :type input_data: TranscribeAudioInput
    :param state: The current agent task state.
    :type state: TaskState
    :param provider: The active backend provider instance.
    :type provider: BackendProvider
    :return: The transcribed text.
    :rtype: str
    """
    logger.info(f"Transcribing audio from file: '{input_data.audio_file_path}'")
    audio_path = Path(input_data.audio_file_path)
    if not audio_path.is_file():
        raise ToolExecutionError(f"Audio file not found at: {audio_path}")

    try:
        audio_bytes = audio_path.read_bytes()
        transcribed_text = await provider.get_transcription(audio_bytes)
        return transcribed_text
    except NotImplementedError:
        raise ToolExecutionError(
            f"The current backend '{state.runtime.backend_profile}' does not support audio transcription."
        )
    except Exception as e:
        logger.exception("Audio transcription tool failed.")
        raise ToolExecutionError(f"Audio transcription failed: {e}")
