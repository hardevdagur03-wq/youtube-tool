"""SEO Service — Phase 8. Main orchestrator with retry, observability, provider independence."""

from __future__ import annotations
import json as _json
import logging
import time
import uuid
from typing import Any

from models.blog_generation import BlogResult
from models.seo_package import SEOOptimizationResult, SEOPackage
from modules.ai.provider import LLMProvider
from modules.ai.provider_factory import create as create_provider
from modules.ai.prompt_builder import version as prompt_version
from modules.seo.seo_optimizer import optimize as run_optimization
from exceptions.seo_errors import SEOError, SEOValidationError
from exceptions.analysis_errors import LLMRateLimitError, LLMTimeoutError
from config.settings import settings, ConfigurationError

logger = logging.getLogger(__name__)
_RETRIES = 3
_BASE_DELAY = 2.0


class SEOService:
    """Orchestrates the full SEO optimization pipeline."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider or self._default_provider()

    @staticmethod
    def _default_provider() -> LLMProvider:
        key = getattr(settings, "gemini_api_key", "") or ""
        if key:
            return create_provider("gemini", key, "gemini-2.5-flash")
        okey = getattr(settings, "openai_api_key", "") or ""
        if okey:
            return create_provider("openai", okey, "gpt-4o-mini")
        raise ConfigurationError(
            "No AI provider API key found. Set GEMINI_API_KEY or OPENAI_API_KEY in your .env file."
        )

    def optimize(
        self,
        blog_data: dict[str, Any],
        video_id: str = "",
        metadata: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> SEOOptimizationResult:
        start = time.time()
        rid = uuid.uuid4().hex[:8]
        logger.info("[%s] SEO optimization: video_id=%s", rid, video_id)

        try:
            blog = BlogResult(**blog_data) if isinstance(blog_data, dict) else blog_data
        except Exception as exc:
            return self._error(video_id, f"Invalid blog data: {exc}", start)

        pk = ""
        sec: list[str] = []
        lt: list[str] = []
        lsi: list[str] = []
        tags: list[str] = []

        if analysis:
            kw = analysis.get("keywords", {})
            pk = kw.get("primary", analysis.get("primary_topic", ""))
            sec = kw.get("secondary", [])
            lt = kw.get("long_tail", [])
            lsi = kw.get("semantic", []) + kw.get("lsi", [])
        if metadata:
            tags = list(metadata.get("tags", []) or [])

        provider = self._resolve(llm_provider, llm_model)
        retries = 0
        last_error: Exception | None = None

        while retries <= _RETRIES:
            try:
                seo_pkg = run_optimization(
                    blog=blog, video_id=video_id,
                    primary_keyword=pk, secondary_keywords=sec,
                    long_tail_keywords=lt, lsi_keywords=lsi,
                    tags=tags, metadata=metadata, provider=provider,
                )
                elapsed = round((time.time() - start) * 1000, 1)
                logger.info(
                    "[%s] SEO done: score=%s, recs=%d, %.1fms",
                    rid, seo_pkg.statistics.seo_score,
                    len(seo_pkg.recommendations), elapsed,
                )
                return SEOOptimizationResult(
                    success=True, video_id=video_id, seo_package=seo_pkg,
                    llm_provider=provider.provider_name, llm_model=provider.model_name,
                    prompt_version=prompt_version(),
                    optimization_time_ms=elapsed,
                )
            except (LLMRateLimitError, LLMTimeoutError) as exc:
                last_error = exc
                retries += 1
                if retries <= _RETRIES:
                    delay = _BASE_DELAY * (2 ** (retries - 1))
                    logger.warning("[%s] Retry %d/%d after %.1fs: %s", rid, retries, _RETRIES, delay, exc)
                    time.sleep(delay)
            except SEOError as exc:
                return self._error(video_id, str(exc), start)
            except Exception as exc:
                logger.exception("[%s] Unexpected: %s", rid, exc)
                return self._error(video_id, f"Unexpected: {exc}", start)

        return self._error(video_id, f"Failed after {_RETRIES} retries: {last_error}", start)

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
        logger.warning("Provider %s not configured, using default", target)
        return self._provider

    @staticmethod
    def _error(video_id: str, error: str, start: float) -> SEOOptimizationResult:
        return SEOOptimizationResult(
            success=False, video_id=video_id, error=error,
            optimization_time_ms=round((time.time() - start) * 1000, 1),
        )
