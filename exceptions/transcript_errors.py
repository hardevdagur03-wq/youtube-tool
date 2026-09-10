class TranscriptError(Exception):
    """Base exception for all transcript-related errors."""
    pass


class TranscriptUnavailableError(TranscriptError):
    """No transcript is available for this video."""
    pass


class TranscriptDisabledError(TranscriptError):
    """Transcripts are disabled for this video."""
    pass


class TranscriptLanguageNotSupportedError(TranscriptError):
    """The requested language is not supported for this video."""
    pass


class TranscriptFetchError(TranscriptError):
    """Failed to fetch transcript from YouTube."""
    pass


class AudioDownloadError(TranscriptError):
    """Failed to download audio from YouTube."""
    pass


class AudioExtractionError(TranscriptError):
    """Failed to extract/convert audio."""
    pass


class TranscriptionError(TranscriptError):
    """Speech-to-text transcription failed."""
    pass


class WhisperModelError(TranscriptError):
    """Whisper model loading or inference failed."""
    pass


class TranscriptQuotaExceededError(TranscriptError):
    """API quota exceeded for transcript service."""
    pass


class TranscriptTimeoutError(TranscriptError):
    """Transcript operation timed out."""
    pass


class TranscriptCleanupError(TranscriptError):
    """Temporary file cleanup failed."""
    pass


class InvalidVideoIdError(TranscriptError):
    """The provided video ID is invalid."""
    pass


class TranscriptCacheError(TranscriptError):
    """Transcript caching operation failed."""
    pass
