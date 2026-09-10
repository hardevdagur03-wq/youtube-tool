"""Custom exceptions for Phase 6 — AI Content Analysis Engine."""


class AnalysisError(Exception):
    """Base exception for all content analysis errors."""


class LLMProviderError(AnalysisError):
    """Raised when the LLM provider fails."""


class LLMAuthenticationError(LLMProviderError):
    """Raised when LLM API key is invalid or missing."""


class LLMRateLimitError(LLMProviderError):
    """Raised when LLM API rate limit is exceeded."""


class LLMContextLengthError(LLMProviderError):
    """Raised when the input exceeds the model's context window."""


class LLMTimeoutError(LLMProviderError):
    """Raised when the LLM request times out."""


class PromptInjectionError(AnalysisError):
    """Raised when prompt injection is detected."""


class InvalidTranscriptError(AnalysisError):
    """Raised when the transcript is invalid for analysis."""


class AnalysisCacheError(AnalysisError):
    """Raised when caching operations fail."""


class AnalysisConfigurationError(AnalysisError):
    """Raised when the analysis configuration is invalid."""
