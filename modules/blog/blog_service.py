"""Blog Generation Service — Phase 7 orchestrator.

Consumes Phase 4/5/6 outputs. Generates SEO blog via provider abstraction.
Retry with exponential backoff. Full observability. Provider-independent.
"""

from __future__ import annotations
import json as _json
import logging
import time
import uuid
from typing import Any

from modules.ai.provider import LLMProvider, ProviderConfig
from modules.ai.prompt_builder import get, version as prompt_version
from modules.ai.response_parser import parse_blog, to_blog_model
from modules.ai.provider_factory import create as create_provider
from modules.blog.blog_generator import generate_blog, generate_full_markdown
from modules.blog.markdown_builder import build as build_markdown
from modules.blog.section_generator import extract as extract_sections
from modules.blog.faq_generator import extract as extract_faq
from modules.blog.toc_generator import generate as generate_toc
from modules.blog.cta_generator import extract_cta
from modules.seo.seo_helper import estimate_score, validate as seo_validate
from modules.seo.keyword_optimizer import KeywordOptimizer
from models.blog_generation import BlogGenerationResult, BlogResult, BlogStatistics
from repositories.blog_repository import BlogRepository
from exceptions.blog_errors import BlogGenerationError, BlogValidationError, BlogInvalidOutput
from exceptions.analysis_errors import LLMRateLimitError, LLMContextLengthError, LLMTimeoutError
from config.settings import settings, ConfigurationError

logger = logging.getLogger(__name__)

_MAX_CHARS = 40000
_DEFAULT_MODEL = "gemini-2.5-flash"
_RETRIES = 3
_BASE_DELAY = 2.0


class BlogGenerationService:
    """Orchestrates blog generation. Provider-agnostic. Configurable."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        repository: BlogRepository | None = None,
    ) -> None:
        self._provider = provider or self._default_provider()
        self._repository = repository or BlogRepository()

    @staticmethod
    def _default_provider() -> LLMProvider:
        key = getattr(settings, "gemini_api_key", "") or ""
        if key:
            return create_provider("gemini", key, _DEFAULT_MODEL)
        okey = getattr(settings, "openai_api_key", "") or ""
        if okey:
            return create_provider("openai", okey, "gpt-4o-mini")
        raise ConfigurationError(
            "No AI provider API key found. Set GEMINI_API_KEY or OPENAI_API_KEY in your .env file."
        )

    def generate(
        self,
        transcript: str,
        video_id: str,
        metadata: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        force_refresh: bool = False,
    ) -> BlogGenerationResult:
        start = time.time()
        rid = uuid.uuid4().hex[:8]
        logger.info("[%s] Blog generation: video_id=%s", rid, video_id)

        if not force_refresh:
            cached = self._repository.get(video_id)
            if cached:
                logger.info("[%s] Cache hit", rid)
                return BlogGenerationResult(**cached)

        try:
            self._validate(transcript, video_id)
        except BlogValidationError as exc:
            return self._error(video_id, str(exc), start)

        provider = self._resolve(llm_provider, llm_model)
        retries = 0
        last_error: Exception | None = None

        while retries <= _RETRIES:
            try:
                blog = self._call(provider, transcript, metadata, analysis)
                result = self._build(blog, video_id, provider, start, rid)
                self._repository.save(video_id, _json.loads(result.model_dump_json()))
                return result
            except (LLMRateLimitError, LLMTimeoutError) as exc:
                last_error = exc
                retries += 1
                if retries <= _RETRIES:
                    delay = _BASE_DELAY * (2 ** (retries - 1))
                    logger.warning("[%s] Retry %d/%d after %.1fs: %s", rid, retries, _RETRIES, delay, exc)
                    time.sleep(delay)
            except (BlogGenerationError, BlogInvalidOutput) as exc:
                return self._error(video_id, str(exc), start)
            except Exception as exc:
                logger.exception("[%s] Unexpected: %s", rid, exc)
                return self._error(video_id, f"Unexpected: {exc}", start)

        return self._error(video_id, f"Failed after {_RETRIES} retries: {last_error}", start)

    def _validate(self, transcript: str, video_id: str) -> None:
        if not video_id or len(video_id) != 11:
            raise BlogValidationError(f"Invalid video ID '{video_id}'")
        if not transcript or not transcript.strip():
            raise BlogValidationError("Transcript is empty")
        if len(transcript) > _MAX_CHARS * 3:
            raise BlogValidationError(f"Transcript too long ({len(transcript)} chars)")

    def _resolve(self, provider_name: str | None, model_name: str | None) -> LLMProvider:
        if not provider_name and not model_name:
            return self._provider
        target = provider_name or self._provider.provider_name
        model = model_name or self._provider.model_name
        if target == "gemini":
            key = getattr(settings, "gemini_api_key", "") or ""
            if key:
                return create_provider("gemini", key, model)
        if target == "openai":
            key = getattr(settings, "openai_api_key", "") or ""
            if key:
                return create_provider("openai", key, model)
        if target == "mock":
            return create_provider("mock", "")
        logger.warning("Provider %s not configured, using default", target)
        return self._provider

    def _call(
        self,
        provider: LLMProvider,
        transcript: str,
        metadata: dict[str, Any] | None,
        analysis: dict[str, Any] | None,
    ) -> BlogResult:
        return generate_blog(provider, transcript, metadata, analysis)

    def _build(
        self,
        blog: BlogResult,
        video_id: str,
        provider: LLMProvider,
        start: float,
        rid: str,
    ) -> BlogGenerationResult:
        elapsed = round((time.time() - start) * 1000, 1)
        md = build_markdown(blog)
        blog.markdown = md
        kw = ""
        if blog.meta_description:
            kw = blog.meta_description.split()[0] if blog.meta_description else ""
        blog.statistics.estimated_seo_score = estimate_score(blog, kw)

        logger.info(
            "[%s] Done: title=%s, words=%d, seo=%s, %.1fms",
            rid, blog.seo_title[:40], blog.statistics.word_count,
            blog.statistics.estimated_seo_score, elapsed,
        )
        return BlogGenerationResult(
            success=True,
            video_id=video_id,
            blog=blog,
            llm_provider=provider.provider_name,
            llm_model=provider.model_name,
            prompt_version=prompt_version(),
            generation_time_ms=elapsed,
        )

    def _error(self, video_id: str, error: str, start: float) -> BlogGenerationResult:
        return BlogGenerationResult(
            success=False,
            video_id=video_id,
            error=error,
            generation_time_ms=round((time.time() - start) * 1000, 1),
        )
