"""Custom exceptions for Phase 8 — SEO Optimization Engine."""


class SEOError(Exception):
    """Base exception for all SEO optimization errors."""


class SEOValidationError(SEOError):
    """Raised when SEO input validation fails."""


class SEOKeywordError(SEOError):
    """Raised when keyword analysis fails."""


class SEOSchemaError(SEOError):
    """Raised when schema generation fails."""


class SEOProviderError(SEOError):
    """Raised when the AI provider fails during SEO generation."""
