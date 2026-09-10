"""Domain service interfaces.

These define the contracts that application services use,
without specifying implementation details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from domain.common.base import DomainService
from domain.entities import Analysis, Blog, Export, SEO, Transcript, Video
from domain.value_objects import VideoId


class TranscriptProvider(DomainService, ABC):
    """Produces a transcript from a video ID."""

    @abstractmethod
    async def get_transcript(
        self, video_id: VideoId, language: str | None = None
    ) -> Transcript:
        ...


class AnalysisProvider(DomainService, ABC):
    """Produces a content analysis from a transcript."""

    @abstractmethod
    async def analyze(
        self, transcript: Transcript, video: Video | None = None
    ) -> Analysis:
        ...


class BlogProvider(DomainService, ABC):
    """Generates a blog post from an analysis."""

    @abstractmethod
    async def generate(
        self, analysis: Analysis, seo: SEO | None = None
    ) -> Blog:
        ...


class SEOProvider(DomainService, ABC):
    """Optimizes a blog post for search engines."""

    @abstractmethod
    async def optimize(
        self, blog: Blog, analysis: Analysis | None = None
    ) -> SEO:
        ...


class ExportProvider(DomainService, ABC):
    """Exports a blog post to one or more formats."""

    @abstractmethod
    async def export(self, blog: Blog, formats: list[str]) -> Export:
        ...


class KnowledgeGraphProvider(DomainService, ABC):
    """Builds a knowledge graph from analysis data."""

    @abstractmethod
    async def build(
        self, analysis: Analysis, transcript: Transcript | None = None
    ) -> Any:
        ...


class OutlineProvider(DomainService, ABC):
    """Generates a blog outline from analysis and SEO data."""

    @abstractmethod
    async def generate(
        self, analysis: Analysis, seo: SEO | None = None
    ) -> Any:
        ...


class LLMProvider(DomainService, ABC):
    """Abstract LLM provider interface for AI services."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        ...

    @abstractmethod
    async def generate_json(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        ...
