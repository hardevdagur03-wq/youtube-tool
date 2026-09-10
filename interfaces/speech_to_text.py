from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionSegment:
    start: float
    end: float
    text: str
    confidence: float | None = None


@dataclass
class TranscriptionResult:
    segments: list[TranscriptionSegment]
    language: str
    language_confidence: float | None = None
    duration_seconds: float | None = None
    processing_time_seconds: float | None = None


class SpeechToTextClient(ABC):
    """Abstract interface for speech-to-text backends.

    Implementations:
        - FasterWhisperClient (local, default)
        - OpenAIWhisperClient (cloud API)
        - DeepgramClient
        - AssemblyAIClient
        - GoogleSpeechClient
    """

    @abstractmethod
    def transcribe(self, audio_path: str, language: str | None = None) -> TranscriptionResult:
        """Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file.
            language: Optional language hint (ISO code).

        Returns:
            ``TranscriptionResult`` with segments and metadata.

        Raises:
            TranscriptionError: If transcription fails.
        """
        pass

    @abstractmethod
    def model_name(self) -> str:
        """Return the model/engine name for logging."""
        pass
