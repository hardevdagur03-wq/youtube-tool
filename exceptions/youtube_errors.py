"""YouTube-specific exception classes for URL processing and API errors."""


class YouTubeURLError(Exception):
    """Base exception for YouTube URL processing errors."""

    def __init__(self, message: str, original_url: str | None = None) -> None:
        self.original_url = original_url
        super().__init__(message)


class InvalidVideoIDError(YouTubeURLError):
    """Raised when a video ID fails validation checks."""
    pass


class UnsupportedURLError(YouTubeURLError):
    """Raised when a URL is valid but refers to an unsupported YouTube resource."""
    pass
