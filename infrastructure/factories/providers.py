"""Factory for creating AI and external service providers.

Eliminates if/else chains for provider creation.
Uses registry pattern for extensibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from domain.services import (
    AnalysisProvider,
    BlogProvider,
    ExportProvider,
    KnowledgeGraphProvider,
    LLMProvider,
    OutlineProvider,
    SEOProvider,
    TranscriptProvider,
)
from infrastructure.config.provider import AppConfig, Config
from infrastructure.feature_flags.flags import feature_flags


class ProviderFactory(ABC):
    @abstractmethod
    def create(self, name: str, config: AppConfig) -> Any:
        ...


class LLMProviderFactory:
    """Creates LLM provider instances by name.

    Providers are registered by name and created on demand.
    """

    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, provider_class: type) -> None:
        cls._registry[name] = provider_class

    @classmethod
    def create(cls, name: str | None = None) -> LLMProvider:
        config = Config.get()
        provider_name = name or config.ai.default_provider

        if not feature_flags.is_enabled(f"{provider_name}_provider"):
            available = cls._find_available()
            if available:
                provider_name = available[0]

        provider_class = cls._registry.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

        return provider_class(config)

    @classmethod
    def _find_available(cls) -> list[str]:
        available = []
        for name in cls._registry:
            if feature_flags.is_enabled(f"{name}_provider"):
                available.append(name)
        return available


class TranscriptProviderFactory:
    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, provider_class: type) -> None:
        cls._registry[name] = provider_class

    @classmethod
    def create(cls, name: str = "youtube") -> TranscriptProvider:
        config = Config.get()
        provider_class = cls._registry.get(name)
        if not provider_class:
            raise ValueError(f"Unknown transcript provider: {name}")
        return provider_class(config)


class AnalysisProviderFactory:
    @staticmethod
    def create(llm_provider: LLMProvider | None = None) -> AnalysisProvider:
        from domain.services import AnalysisProvider as AP
        return _create_analysis_provider(llm_provider)


class BlogProviderFactory:
    @staticmethod
    def create(llm_provider: LLMProvider | None = None) -> BlogProvider:
        return _create_blog_provider(llm_provider)


class SEOProviderFactory:
    @staticmethod
    def create(llm_provider: LLMProvider | None = None) -> SEOProvider:
        return _create_seo_provider(llm_provider)


class ExportProviderFactory:
    @staticmethod
    def create() -> ExportProvider:
        return _create_export_provider()


def _create_analysis_provider(llm: LLMProvider | None = None) -> AnalysisProvider:
    """Create analysis provider with dependency injection."""
    from domain.services import AnalysisProvider
    # Wrap the actual implementation with DI
    return _AnalysisProviderAdapter(llm)


def _create_blog_provider(llm: LLMProvider | None = None) -> BlogProvider:
    return _BlogProviderAdapter(llm)


def _create_seo_provider(llm: LLMProvider | None = None) -> SEOProvider:
    return _SEOProviderAdapter(llm)


def _create_export_provider() -> ExportProvider:
    return _ExportProviderAdapter()


class _AnalysisProviderAdapter(AnalysisProvider):
    """Adapter that delegates to existing ContentAnalysisService."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    async def analyze(self, transcript: Any, video: Any = None) -> Any:
        from domain.entities import Analysis
        from domain.value_objects import AnalysisSummary, ContentCategory, ContentType, KeywordSet, QualityScores, SearchIntent
        from services.content_analysis_service import ContentAnalysisService

        service = ContentAnalysisService()
        text = transcript.clean_text or transcript.plain_text
        meta = video.raw_metadata if video and hasattr(video, 'raw_metadata') else None

        result = service.analyze(
            transcript=text,
            video_id=transcript.video_id.value,
            metadata=meta,
        )
        return Analysis(
            video_id=transcript.video_id,
            primary_topic=result.primary_topic if hasattr(result, 'primary_topic') else "",
            summary=AnalysisSummary(short=str(getattr(result, 'summary', ''))),
            keywords=KeywordSet(),
            quality_scores=QualityScores(),
            raw_data=result.model_dump() if hasattr(result, 'model_dump') else {},
        )


class _BlogProviderAdapter(BlogProvider):
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    async def generate(self, analysis: Any, seo: Any = None) -> Any:
        from domain.entities import Blog
        from domain.value_objects import BlogStatistics
        from modules.blog.blog_service import BlogGenerationService

        service = BlogGenerationService()
        transcript_text = getattr(analysis, 'raw_data', {}).get('transcript', '')
        video_id = analysis.video_id.value if hasattr(analysis, 'video_id') else ''

        result = service.generate(
            transcript=transcript_text,
            video_id=video_id,
        )
        stats = BlogStatistics(
            word_count=getattr(result, 'word_count', 0) or 0,
        )
        return Blog(
            video_id=analysis.video_id,
            markdown=getattr(result, 'markdown', '') or '',
            statistics=stats,
            raw_data=result.model_dump() if hasattr(result, 'model_dump') else {},
        )


class _SEOProviderAdapter(SEOProvider):
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    async def optimize(self, blog: Any, analysis: Any = None) -> Any:
        from domain.entities import SEO
        from domain.value_objects import SEOScore
        from modules.seo.seo_service import SEOService

        blog_data = blog.raw_data if hasattr(blog, 'raw_data') else {}
        video_id = blog.video_id.value if hasattr(blog, 'video_id') else ''

        service = SEOService()
        result = service.optimize(blog_data=blog_data, video_id=video_id)
        return SEO(
            video_id=blog.video_id,
            scores=SEOScore(),
            raw_data=result.model_dump() if hasattr(result, 'model_dump') else {},
        )


class _ExportProviderAdapter(ExportProvider):
    async def export(self, blog: Any, formats: list[str]) -> Any:
        from domain.entities import Export
        from domain.value_objects import ExportFormat, ExportStatus
        from export.engine import ExportEngine
        from models.blog_export import ExportRequest

        blog_data = blog.raw_data if hasattr(blog, 'raw_data') else {}
        engine = ExportEngine()

        req = ExportRequest(
            blog_title=blog_data.get('seo_title', ''),
            formats=formats,
        )
        result = engine.export(req)
        return Export(
            video_id=blog.video_id,
            blog_id=blog.id,
            status=ExportStatus.COMPLETED if getattr(result, 'success', False) else ExportStatus.FAILED,
            formats=[ExportFormat(f) for f in formats],
            raw_data=result.model_dump() if hasattr(result, 'model_dump') else {},
        )
