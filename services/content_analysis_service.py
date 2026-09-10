"""Content Analysis Service — main orchestrator for Phase 6.

Transforms a processed transcript into structured semantic intelligence
that powers all downstream AI modules (blog, SEO, social, newsletter, etc.).
"""

from __future__ import annotations
import logging
import time
import uuid
from typing import Any

from models.content_analysis import (
    ContentAnalysisResult,
    AnalysisSummary,
    KeywordSet,
    EntitySet,
    ContentOutline,
    QualityScores,
    SearchIntent,
    ContentCategory,
    ContentType,
    DifficultyLevel,
)
from providers.llm_provider import LLMProvider, MockProvider, ProviderConfig, create_provider
from utils.prompt_builder import build_analysis_prompt, get_system_prompt, get_prompt_version
from utils.confidence import compute_confidence, compute_depth_score
from repositories.analysis_repository import AnalysisRepository
from exceptions.analysis_errors import AnalysisError, InvalidTranscriptError
from exceptions.processing_errors import ValidationError
from config.settings import settings

logger = logging.getLogger(__name__)

_DEFAULT_LLM_MODEL = "gpt-4o-mini"
_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_MAX_TRANSCRIPT_LENGTH = 80000


class ContentAnalysisService:
    """Service that orchestrates the full AI content analysis pipeline."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        repository: AnalysisRepository | None = None,
    ) -> None:
        self._provider = provider or self._create_default_provider()
        self._repository = repository or AnalysisRepository()

    @staticmethod
    def _create_default_provider() -> LLMProvider:
        gemini_key = getattr(settings, "gemini_api_key", "") or ""
        openai_key = getattr(settings, "openai_api_key", "") or ""
        if gemini_key:
            return create_provider(
                ProviderConfig(
                    api_key=gemini_key,
                    model=_DEFAULT_GEMINI_MODEL,
                    temperature=0.1,
                    extra={"provider": "gemini"},
                )
            )
        if openai_key:
            return create_provider(
                ProviderConfig(
                    api_key=openai_key,
                    model=_DEFAULT_LLM_MODEL,
                    temperature=0.1,
                )
            )
        return create_provider(ProviderConfig(temperature=0.1))

    def analyze(
        self,
        transcript: str,
        video_id: str,
        metadata: dict[str, Any] | None = None,
        video_statistics: dict[str, Any] | None = None,
        channel_info: dict[str, Any] | None = None,
        language_info: dict[str, Any] | None = None,
        force_refresh: bool = False,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> ContentAnalysisResult:
        """Analyze a processed transcript and return structured semantic intelligence.

        Args:
            transcript: Clean, processed transcript text (from Phase 5).
            video_id: 11-character YouTube video ID.
            metadata: Optional video metadata dict.
            video_statistics: Optional video statistics dict.
            channel_info: Optional channel information dict.
            language_info: Optional language distribution dict.
            force_refresh: If true, bypass cache.
            llm_provider: Override LLM provider name.
            llm_model: Override LLM model name.

        Returns:
            ``ContentAnalysisResult`` with full semantic intelligence.
        """
        overall_start = time.time()
        rid = uuid.uuid4().hex[:8]
        logger.info("[%s] Content analysis started: video_id=%s", rid, video_id)

        if not force_refresh:
            cached = self._repository.get(video_id)
            if cached is not None:
                logger.info("[%s] Cache hit for %s", rid, video_id)
                return cached

        try:
            self._validate_input(transcript, video_id)
        except (ValidationError, InvalidTranscriptError) as exc:
            logger.error("[%s] Validation failed: %s", rid, exc)
            return ContentAnalysisResult(
                success=False, video_id=video_id, error=str(exc),
                analysis_time_ms=round((time.time() - overall_start) * 1000, 1),
            )

        provider = self._get_provider(llm_provider, llm_model)

        try:
            raw = self._call_llm(provider, transcript, video_id, language_info)
            result = self._build_result(raw, video_id, provider, overall_start)
        except AnalysisError as exc:
            logger.error("[%s] Analysis failed: %s", rid, exc)
            return ContentAnalysisResult(
                success=False, video_id=video_id, error=str(exc),
                analysis_time_ms=round((time.time() - overall_start) * 1000, 1),
            )

        self._repository.save(video_id, result)
        logger.info(
            "[%s] Analysis complete: topic=%s, intent=%s, tokens=%d, %.1fms",
            rid, result.primary_topic, result.search_intent.value,
            result.total_tokens, result.analysis_time_ms,
        )
        return result

    def _validate_input(self, transcript: str, video_id: str) -> None:
        if not video_id or len(video_id) != 11:
            raise InvalidTranscriptError(f"Invalid video ID '{video_id}'. Must be exactly 11 characters.")
        if not transcript or not transcript.strip():
            raise InvalidTranscriptError("Transcript is empty.")
        if len(transcript) > _MAX_TRANSCRIPT_LENGTH * 2:
            raise InvalidTranscriptError(f"Transcript too long ({len(transcript)} chars).")

    def _get_provider(self, provider_name: str | None, model_name: str | None) -> LLMProvider:
        if provider_name or model_name:
            api_key = getattr(settings, "openai_api_key", "") or ""
            return create_provider(
                ProviderConfig(
                    api_key=api_key,
                    model=model_name or _DEFAULT_LLM_MODEL,
                    temperature=0.1,
                )
            )
        return self._provider

    def _call_llm(
        self,
        provider: LLMProvider,
        transcript: str,
        video_id: str,
        language_info: dict[str, Any] | None,
    ) -> dict[str, Any]:
        language = "en"
        if language_info and isinstance(language_info, dict):
            language = language_info.get("primary", "en")

        categories = ""
        prompt = build_analysis_prompt(transcript, video_id, categories, language)
        system = get_system_prompt()

        if isinstance(provider, MockProvider):
            return provider.generate_json(prompt, system)

        return provider.generate_json(prompt, system)

    def _build_result(
        self,
        raw: dict[str, Any],
        video_id: str,
        provider: LLMProvider,
        start_time: float,
    ) -> ContentAnalysisResult:
        elapsed = round((time.time() - start_time) * 1000, 1)

        summary_data = raw.get("summary", {})
        keywords_data = raw.get("keywords", {})
        entities_data = raw.get("entities", {})
        outline_data = raw.get("outline", {})
        quality_data = raw.get("quality", {})

        entity_count = sum(len(v) for v in entities_data.values() if isinstance(v, list))
        keyword_count = (
            len(keywords_data.get("secondary", []))
            + len(keywords_data.get("long_tail", []))
            + len(keywords_data.get("lsi", []))
        )
        outline_sections = len(outline_data.get("sections", []))

        summary = AnalysisSummary(**{
            k: v for k, v in summary_data.items()
            if k in AnalysisSummary.model_fields and v is not None
        }) if summary_data else AnalysisSummary()

        keywords = KeywordSet(**{
            k: v for k, v in keywords_data.items()
            if k in KeywordSet.model_fields and v is not None
        }) if keywords_data else KeywordSet()

        entities = EntitySet(**{
            k: v for k, v in entities_data.items()
            if k in EntitySet.model_fields and v is not None
        }) if entities_data else EntitySet()

        outline = ContentOutline(**{
            k: v for k, v in outline_data.items()
            if k in ContentOutline.model_fields and v is not None
        }) if outline_data else ContentOutline()

        q = quality_data or {}
        quality = QualityScores(
            topic_coverage=float(q.get("topic_coverage", 0)),
            depth_score=float(q.get("depth_score", compute_depth_score(0, entity_count, keyword_count, outline_sections))),
            readability=float(q.get("readability", 70)),
            information_density=float(q.get("information_density", 50)),
            technical_complexity=float(q.get("technical_complexity", 40)),
            educational_value=float(q.get("educational_value", 60)),
            uniqueness=float(q.get("uniqueness", 50)),
            seo_potential=float(q.get("seo_potential", 60)),
            evergreen_score=float(q.get("evergreen_score", 50)),
            engagement_potential=float(q.get("engagement_potential", 60)),
            confidence=float(q.get("confidence", compute_confidence(0, 0, bool(entity_count), bool(keyword_count), bool(outline_sections)))),
        )

        return ContentAnalysisResult(
            success=True,
            video_id=video_id,
            primary_topic=raw.get("primary_topic", ""),
            secondary_topics=raw.get("secondary_topics", []),
            category=self._parse_category(raw.get("category", "")),
            subcategory=raw.get("subcategory", ""),
            content_type=self._parse_content_type(raw.get("content_type", "")),
            search_intent=self._parse_intent(raw.get("search_intent", "")),
            intent_confidence=float(raw.get("intent_confidence", 0.0)),
            target_audience=raw.get("target_audience", ""),
            experience_level=self._parse_difficulty(raw.get("experience_level", "")),
            industry=raw.get("industry", ""),
            difficulty=raw.get("difficulty", ""),
            content_purpose=raw.get("content_purpose", ""),
            problem_statement=raw.get("problem_statement", ""),
            main_solution=raw.get("main_solution", ""),
            key_takeaways=raw.get("key_takeaways", []),
            pain_points=raw.get("pain_points", []),
            opportunities=raw.get("opportunities", []),
            action_items=raw.get("action_items", []),
            call_to_actions=raw.get("call_to_actions", []),
            learning_objectives=raw.get("learning_objectives", []),
            business_value=raw.get("business_value", ""),
            educational_value=raw.get("educational_value", ""),
            summary=summary,
            keywords=keywords,
            entities=entities,
            outline=outline,
            quality=quality,
            analysis_time_ms=elapsed,
            llm_provider=provider.provider_name,
            llm_model=provider.model_name,
            prompt_version=get_prompt_version(),
            total_tokens=0,
            input_tokens=0,
            output_tokens=0,
            cost_estimate=0.0,
            error=None,
        )

    @staticmethod
    def _parse_intent(value: str) -> SearchIntent:
        for intent in SearchIntent:
            if intent.value == value.lower().strip():
                return intent
        return SearchIntent.INFORMATIONAL

    @staticmethod
    def _parse_category(value: str) -> ContentCategory:
        for cat in ContentCategory:
            if cat.value == value.lower().strip():
                return cat
        return ContentCategory.OTHER

    @staticmethod
    def _parse_content_type(value: str) -> ContentType:
        for ct in ContentType:
            if ct.value == value.lower().strip():
                return ct
        return ContentType.OTHER

    @staticmethod
    def _parse_difficulty(value: str) -> DifficultyLevel:
        for d in DifficultyLevel:
            if d.value == value.lower().strip():
                return d
        return DifficultyLevel.ALL
