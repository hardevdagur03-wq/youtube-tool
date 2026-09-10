"""Custom exceptions for Phase 6 — Blog Generation Engine."""


class BlogGenerationError(Exception):
    """Base exception for all blog generation errors."""


class BlogValidationError(BlogGenerationError):
    """Raised when blog input validation fails."""


class BlogContextTooLong(BlogGenerationError):
    """Raised when the combined context exceeds token limits."""


class BlogInvalidOutput(BlogGenerationError):
    """Raised when the LLM output cannot be parsed into a valid blog."""


class BlogSEOScoreError(BlogGenerationError):
    """Raised when SEO validation fails."""
