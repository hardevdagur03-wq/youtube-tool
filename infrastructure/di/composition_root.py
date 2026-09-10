"""Composition Root — wires all layers together.

This is the only place where dependency injection wiring happens.
The rest of the application uses constructor injection.
"""

from __future__ import annotations

from typing import Any

from application.use_cases.pipeline import RunPipelineUseCase
from application.use_cases.video import (
    CreateVideoUseCase,
    GetVideoQueryHandler,
    ListVideosQueryHandler,
)
from domain.repositories import UnitOfWork
from infrastructure.caching.abstraction import CacheService, InMemoryCache
from infrastructure.config.provider import Config
from infrastructure.di.container import container
from infrastructure.factories.providers import (
    AnalysisProviderFactory,
    BlogProviderFactory,
    ExportProviderFactory,
    LLMProviderFactory,
    SEOProviderFactory,
    TranscriptProviderFactory,
)
from infrastructure.feature_flags.flags import FeatureFlagManager, feature_flags


def wire(config: Any = None) -> None:
    """Wire all dependencies for the application.

    Must be called once at application startup.
    """
    app_config = config or Config.get()

    # --- Infrastructure ---
    cache_service = CacheService(backend=InMemoryCache())
    container.register_instance("cache", cache_service)
    container.register_instance("config", app_config)
    container.register_instance("feature_flags", feature_flags)

    # --- Repositories (infrastructure implements domain interfaces) ---
    _register_repositories()

    # --- Unit of Work ---
    _register_uow()

    # --- Domain Services (providers) ---
    container.register("llm_provider", lambda c: LLMProviderFactory.create(), singleton=True)
    container.register("transcript_provider", lambda c: TranscriptProviderFactory.create(), singleton=True)
    container.register("analysis_provider", lambda c: AnalysisProviderFactory.create(c.resolve("llm_provider")), singleton=True)
    container.register("blog_provider", lambda c: BlogProviderFactory.create(c.resolve("llm_provider")), singleton=True)
    container.register("seo_provider", lambda c: SEOProviderFactory.create(c.resolve("llm_provider")), singleton=True)
    container.register("export_provider", lambda c: ExportProviderFactory.create(), singleton=True)

    # --- Application Use Cases ---
    container.register(
        "create_video_use_case",
        lambda c: CreateVideoUseCase(c.resolve("uow")),
        singleton=False,
    )
    container.register(
        "get_video_query_handler",
        lambda c: GetVideoQueryHandler(c.resolve("uow")),
        singleton=False,
    )
    container.register(
        "list_videos_query_handler",
        lambda c: ListVideosQueryHandler(c.resolve("uow")),
        singleton=False,
    )
    container.register(
        "run_pipeline_use_case",
        lambda c: RunPipelineUseCase(
            uow=c.resolve("uow"),
            transcript_provider=c.resolve("transcript_provider"),
            analysis_provider=c.resolve("analysis_provider"),
            blog_provider=c.resolve("blog_provider"),
            seo_provider=c.resolve("seo_provider"),
            export_provider=c.resolve("export_provider"),
        ),
        singleton=False,
    )


def _register_repositories() -> None:
    """Register repository implementations.

    Repositories are implemented in the infrastructure layer
    and implement interfaces defined in the domain layer.
    """
    try:
        from infrastructure.repositories.sqlalchemy_repos import (
            SQLAlchemyUnitOfWork,
        )
        container.register("uow", lambda c: SQLAlchemyUnitOfWork(), singleton=False)
    except ImportError:
        from infrastructure.repositories.memory_repos import (
            InMemoryUnitOfWork,
        )
        container.register("uow", lambda c: InMemoryUnitOfWork(), singleton=False)


def _register_uow() -> None:
    """Unit of Work is already registered via _register_repositories."""
    pass


def reset_for_testing() -> None:
    """Reset all container registrations for test isolation."""
    container.clear()
    feature_flags._flags.clear()
    from infrastructure.feature_flags.flags import DEFAULT_FLAGS
    for flag in DEFAULT_FLAGS:
        feature_flags.register(flag)
