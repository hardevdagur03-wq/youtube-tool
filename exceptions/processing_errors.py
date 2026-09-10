"""Exception hierarchy for the transcript processing pipeline."""


class ProcessingError(Exception):
    """Base exception for all processing pipeline errors."""


class ValidationError(ProcessingError):
    """Input validation failed."""


class EmptyTranscriptError(ValidationError):
    """Transcript is empty or contains no usable text."""


class InvalidLanguageError(ValidationError):
    """Unsupported or invalid language detected."""


class UnicodeError(ProcessingError):
    """Unicode normalization or decoding failure."""


class CaptionMergeError(ProcessingError):
    """Failed to merge caption segments."""


class PunctuationError(ProcessingError):
    """Punctuation restoration failed."""


class SentenceRestoreError(ProcessingError):
    """Sentence boundary detection failed."""


class ParagraphDetectionError(ProcessingError):
    """Paragraph boundary detection failed."""


class ProcessingTimeoutError(ProcessingError):
    """Pipeline stage exceeded maximum allowed time."""


class ProcessingLimitError(ProcessingError):
    """Transcript exceeds maximum allowed size."""


class QualityCheckFailed(ProcessingError):
    """Transcript failed quality validation after processing."""


class ProcessorError(ProcessingError):
    """Generic processor-level failure."""
