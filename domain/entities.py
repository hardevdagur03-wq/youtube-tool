"""Domain entities for the YouTube SEO Blog platform.

These entities have zero framework dependencies.
They represent the core business concepts of the application.
"""

from __future__ import annotations

from typing import Any

from domain.common.base import AggregateRoot
from domain.value_objects import (
    AnalysisSummary,
    BlogSection,
    BlogStatistics,
    ContentCategory,
    ContentType,
    DifficultyLevel,
    ExportFile,
    ExportFormat,
    ExportStatus,
    KeywordSet,
    PipelineStage,
    PipelineStatus,
    QualityScores,
    SEOScore,
    SearchIntent,
    TranscriptSegment,
    TranscriptSource,
    VideoId,
)


class Video(AggregateRoot):
    """A YouTube video - the root entity of the platform."""

    def __init__(
        self,
        video_id: VideoId,
        title: str = "",
        description: str = "",
        channel_name: str = "",
        channel_id: str = "",
        published_at: str = "",
        duration_seconds: int = 0,
        view_count: int = 0,
        like_count: int = 0,
        comment_count: int = 0,
        thumbnail_url: str = "",
        language: str = "",
        category: str = "",
        tags: list[str] | None = None,
        raw_metadata: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.title = title
        self.description = description
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.published_at = published_at
        self.duration_seconds = duration_seconds
        self.view_count = view_count
        self.like_count = like_count
        self.comment_count = comment_count
        self.thumbnail_url = thumbnail_url
        self.language = language
        self.category = category
        self.tags = tags or []
        self.raw_metadata = raw_metadata or {}


class Transcript(AggregateRoot):
    """A video transcript from any source."""

    def __init__(
        self,
        video_id: VideoId,
        source: TranscriptSource = TranscriptSource.MANUAL,
        language: str = "",
        segments: list[TranscriptSegment] | None = None,
        plain_text: str = "",
        word_count: int = 0,
        duration_seconds: float = 0.0,
        is_processed: bool = False,
        clean_text: str = "",
        processing_steps: list[dict] | None = None,
        raw_data: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.source = source
        self.language = language
        self.segments = segments or []
        self.plain_text = plain_text
        self.word_count = word_count
        self.duration_seconds = duration_seconds
        self.is_processed = is_processed
        self.clean_text = clean_text
        self.processing_steps = processing_steps or []
        self.raw_data = raw_data or {}


class Analysis(AggregateRoot):
    """AI-powered content analysis of a transcript."""

    def __init__(
        self,
        video_id: VideoId,
        primary_topic: str = "",
        secondary_topics: list[str] | None = None,
        category: ContentCategory = ContentCategory.OTHER,
        content_type: ContentType = ContentType.OTHER,
        search_intent: SearchIntent = SearchIntent.INFORMATIONAL,
        target_audience: str = "",
        difficulty: DifficultyLevel = DifficultyLevel.ALL_LEVELS,
        summary: AnalysisSummary | None = None,
        keywords: KeywordSet | None = None,
        entities: list[dict] | None = None,
        quality_scores: QualityScores | None = None,
        key_takeaways: list[str] | None = None,
        pain_points: list[str] | None = None,
        llm_provider: str = "",
        llm_model: str = "",
        prompt_version: str = "",
        total_tokens: int = 0,
        cost: float = 0.0,
        raw_data: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.primary_topic = primary_topic
        self.secondary_topics = secondary_topics or []
        self.category = category
        self.content_type = content_type
        self.search_intent = search_intent
        self.target_audience = target_audience
        self.difficulty = difficulty
        self.summary = summary or AnalysisSummary()
        self.keywords = keywords or KeywordSet()
        self.entities = entities or []
        self.quality_scores = quality_scores or QualityScores()
        self.key_takeaways = key_takeaways or []
        self.pain_points = pain_points or []
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.prompt_version = prompt_version
        self.total_tokens = total_tokens
        self.cost = cost
        self.raw_data = raw_data or {}


class Blog(AggregateRoot):
    """A generated blog post."""

    def __init__(
        self,
        video_id: VideoId,
        seo_title: str = "",
        meta_description: str = "",
        slug: str = "",
        introduction: str = "",
        sections: list[BlogSection] | None = None,
        conclusion: str = "",
        call_to_action: str = "",
        faq_items: list[dict] | None = None,
        markdown: str = "",
        statistics: BlogStatistics | None = None,
        llm_provider: str = "",
        llm_model: str = "",
        total_tokens: int = 0,
        cost: float = 0.0,
        raw_data: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.seo_title = seo_title
        self.meta_description = meta_description
        self.slug = slug
        self.introduction = introduction
        self.sections = sections or []
        self.conclusion = conclusion
        self.call_to_action = call_to_action
        self.faq_items = faq_items or []
        self.markdown = markdown
        self.statistics = statistics or BlogStatistics()
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.total_tokens = total_tokens
        self.cost = cost
        self.raw_data = raw_data or {}


class SEO(AggregateRoot):
    """SEO optimization for a blog post."""

    def __init__(
        self,
        video_id: VideoId,
        meta_title: str = "",
        meta_description: str = "",
        slug: str = "",
        canonical_url: str = "",
        focus_keywords: list[str] | None = None,
        secondary_keywords: list[str] | None = None,
        keyword_density: dict[str, float] | None = None,
        internal_links: list[dict] | None = None,
        external_links: list[dict] | None = None,
        schema_markup: dict[str, Any] | None = None,
        open_graph: dict[str, str] | None = None,
        twitter_card: dict[str, str] | None = None,
        scores: SEOScore | None = None,
        recommendations: list[dict] | None = None,
        llm_provider: str = "",
        llm_model: str = "",
        total_tokens: int = 0,
        cost: float = 0.0,
        raw_data: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.meta_title = meta_title
        self.meta_description = meta_description
        self.slug = slug
        self.canonical_url = canonical_url
        self.focus_keywords = focus_keywords or []
        self.secondary_keywords = secondary_keywords or []
        self.keyword_density = keyword_density or {}
        self.internal_links = internal_links or []
        self.external_links = external_links or []
        self.schema_markup = schema_markup or {}
        self.open_graph = open_graph or {}
        self.twitter_card = twitter_card or {}
        self.scores = scores or SEOScore()
        self.recommendations = recommendations or []
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.total_tokens = total_tokens
        self.cost = cost
        self.raw_data = raw_data or {}


class Export(AggregateRoot):
    """An export of a blog post in one or more formats."""

    def __init__(
        self,
        video_id: VideoId,
        blog_id: str = "",
        formats: list[ExportFormat] | None = None,
        status: ExportStatus = ExportStatus.PENDING,
        files: list[ExportFile] | None = None,
        zip_url: str = "",
        total_size_bytes: int = 0,
        error_message: str = "",
        raw_data: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.blog_id = blog_id
        self.formats = formats or [ExportFormat.MARKDOWN]
        self.status = status
        self.files = files or []
        self.zip_url = zip_url
        self.total_size_bytes = total_size_bytes
        self.error_message = error_message
        self.raw_data = raw_data or {}


class Project(AggregateRoot):
    """A project that tracks the pipeline state for a video."""

    def __init__(
        self,
        video_id: VideoId,
        url: str = "",
        title: str = "",
        status: PipelineStatus = PipelineStatus.PENDING,
        current_stage: PipelineStage = PipelineStage.METADATA,
        completed_stages: list[PipelineStage] | None = None,
        failed_stages: list[PipelineStage] | None = None,
        progress: float = 0.0,
        error_message: str = "",
        metadata: dict[str, Any] | None = None,
        run_count: int = 0,
        last_run_at: str = "",
        created_at: str = "",
        updated_at: str = "",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.url = url
        self.title = title
        self.status = status
        self.current_stage = current_stage
        self.completed_stages = completed_stages or []
        self.failed_stages = failed_stages or []
        self.progress = progress
        self.error_message = error_message
        self.metadata = metadata or {}
        self.run_count = run_count
        self.last_run_at = last_run_at
        self.created_at = created_at
        self.updated_at = updated_at

    def complete_stage(self, stage: PipelineStage) -> None:
        self.completed_stages.append(stage)
        self.current_stage = self._next_stage(stage)

    def fail_stage(self, stage: PipelineStage, error: str) -> None:
        self.failed_stages.append(stage)
        self.error_message = error
        self.status = PipelineStatus.FAILED

    def _next_stage(self, current: PipelineStage) -> PipelineStage:
        stages = list(PipelineStage)
        try:
            idx = stages.index(current)
            if idx + 1 < len(stages):
                return stages[idx + 1]
        except ValueError:
            pass
        return current


class KnowledgeGraph(AggregateRoot):
    """Knowledge graph for a video."""

    def __init__(
        self,
        video_id: VideoId,
        entities: list[dict] | None = None,
        relationships: list[dict] | None = None,
        summary: dict[str, Any] | None = None,
        raw_data: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.entities = entities or []
        self.relationships = relationships or []
        self.summary = summary or {}
        self.raw_data = raw_data or {}

    def entity_count(self) -> int:
        return len(self.entities)

    def relationship_count(self) -> int:
        return len(self.relationships)


class Outline(AggregateRoot):
    """Content outline for a blog post."""

    def __init__(
        self,
        video_id: VideoId,
        title: str = "",
        sections: list[dict] | None = None,
        summary: dict[str, Any] | None = None,
        raw_data: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.video_id = video_id
        self.title = title
        self.sections = sections or []
        self.summary = summary or {}
        self.raw_data = raw_data or {}
