"""Base validator interface for the review engine."""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
import time
from typing import Any

from models.blog_review import BlogReviewRequest

logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """Abstract base for all review validators."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable validator name."""
        pass

    @abstractmethod
    def validate(self, request: BlogReviewRequest) -> Any:
        """Run validation and return result model."""
        pass

    def execute(self, request: BlogReviewRequest) -> tuple[Any, float]:
        """Execute with timing. Returns (result, elapsed_ms)."""
        start = time.time()
        try:
            result = self.validate(request)
            elapsed = round((time.time() - start) * 1000, 1)
            logger.info("[Review] %s completed in %.1fms", self.name(), elapsed)
            return result, elapsed
        except Exception as exc:
            elapsed = round((time.time() - start) * 1000, 1)
            logger.exception("[Review] %s failed after %.1fms: %s", self.name(), elapsed, exc)
            raise
