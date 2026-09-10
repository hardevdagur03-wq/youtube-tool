"""Section Generator — generates each section independently via LLM.

Generates Introduction, Body sections, FAQ, Conclusion, CTA.
Each section is a fully independent LLM call with its own prompt,
context, retry, and validation.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from section_generation.section_models import (
    SectionType,
    SectionStatus,
    SectionContext,
    SectionPrompt,
    SectionOutput,
    GenerationResult,
    GenerationConfig,
    generate_section_id,
    estimate_reading_time_seconds,
    utc_now,
)
from section_generation.prompt_builder import PromptBuilder
from section_generation.context_manager import ContextManager
from section_generation.section_cache import SectionCache

logger = logging.getLogger(__name__)


class SectionGenerator:
    """Generates individual blog sections via LLM.

    Each section is an independent generation unit with its own:
    - Prompt
    - Context
    - Cache
    - Retry
    - Validation
    - Version
    - Logs
    - Metrics
    - Output
    """

    def __init__(
        self,
        prompt_builder: PromptBuilder | None = None,
        context_manager: ContextManager | None = None,
        section_cache: SectionCache | None = None,
        llm_provider: Any = None,
    ) -> None:
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._context_manager = context_manager or ContextManager()
        self._cache = section_cache or SectionCache()
        self._llm = llm_provider

    def set_llm_provider(self, provider: Any) -> None:
        self._llm = provider

    def generate(
        self,
        section_type: SectionType,
        context: SectionContext,
        config: GenerationConfig | None = None,
    ) -> SectionOutput:
        cfg = config or GenerationConfig()
        section_id = generate_section_id(section_type, context.order)
        heading = context.heading

        cached = self._try_cache(section_type, context, section_id, cfg)
        if cached:
            return cached

        prompt = self._prompt_builder.build(context, section_type)

        result = self._generate_with_retry(
            section_type=section_type,
            prompt=prompt,
            config=cfg,
            section_id=section_id,
        )

        output = self._build_output(
            section_id=section_id,
            section_type=section_type,
            heading=heading,
            context=context,
            result=result,
        )

        if result.success and cfg.enable_cache:
            self._cache.set(section_type, context, output)

        return output

    def _try_cache(
        self,
        section_type: SectionType,
        context: SectionContext,
        section_id: str,
        config: GenerationConfig,
    ) -> SectionOutput | None:
        if not config.enable_cache:
            return None
        cached = self._cache.get(section_type, context)
        if cached is not None:
            h = context.heading
            cached.section_id = section_id
            cached.heading = h
            cached.order = context.order
            cached.word_count = len(cached.content.split())
            cached.reading_time_seconds = estimate_reading_time_seconds(cached.word_count)
            cached.status = SectionStatus.CACHED
            logger.info(
                "Cache hit for %s section '%s' (%d words)",
                section_type.value, h, cached.word_count,
            )
            return cached
        return None

    def _generate_with_retry(
        self,
        section_type: SectionType,
        prompt: SectionPrompt,
        config: GenerationConfig,
        section_id: str,
    ) -> GenerationResult:
        last_error = ""
        retry_count = 0

        for attempt in range(config.max_retries + 1):
            try:
                result = self._call_llm(prompt, config, section_type)
                result.retry_count = retry_count
                return result
            except Exception as exc:
                last_error = str(exc)
                retry_count = attempt + 1
                logger.warning(
                    "Section %s (%s) attempt %d/%d failed: %s",
                    section_id, section_type.value,
                    attempt + 1, config.max_retries + 1, exc,
                )
                if attempt < config.max_retries:
                    delay = self._compute_delay(attempt, config)
                    time.sleep(delay)

        logger.error(
            "Section %s (%s) failed after %d retries: %s",
            section_id, section_type.value, retry_count, last_error,
        )
        return GenerationResult(
            success=False,
            error=last_error or "Unknown error",
            retry_count=retry_count,
        )

    def _call_llm(
        self,
        prompt: SectionPrompt,
        config: GenerationConfig,
        section_type: SectionType,
    ) -> GenerationResult:
        if self._llm is None:
            return GenerationResult(
                success=True,
                content=self._mock_generate(section_type, prompt),
                tokens_input=prompt.prompt_tokens_estimate,
                tokens_output=100,
            )

        start = time.time()
        try:
            response = self._llm.generate(prompt.user_prompt, prompt.system_prompt)
            elapsed = (time.time() - start) * 1000
            content = response.text.strip()

            return GenerationResult(
                success=True,
                content=content,
                tokens_input=response.input_tokens or prompt.prompt_tokens_estimate,
                tokens_output=response.output_tokens or len(content) // 4,
                tokens_used=(response.input_tokens or 0) + (response.output_tokens or 0),
                latency_ms=elapsed,
                cost_estimate=getattr(response, "cost_estimate", 0.0),
            )
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            return GenerationResult(
                success=False,
                error=str(exc),
                latency_ms=elapsed,
            )

    def _build_output(
        self,
        section_id: str,
        section_type: SectionType,
        heading: str,
        context: SectionContext,
        result: GenerationResult,
    ) -> SectionOutput:
        content = result.content if result.success else ""
        word_count = len(content.split())

        output = SectionOutput(
            section_id=section_id,
            section_type=section_type,
            heading=heading,
            content=content,
            order=context.order,
            word_count=word_count,
            reading_time_seconds=estimate_reading_time_seconds(word_count),
            keywords_used=[k for k in context.keywords[:5] if k.lower() in content.lower()],
            entities_used=[e for e in context.entities[:5] if e.lower() in content.lower()],
            facts_used=[f for f in context.facts[:3] if any(t.lower() in content.lower() for t in f.split()[:3])],
            version=1,
            generation_time_ms=result.latency_ms,
            tokens_input=result.tokens_input,
            tokens_output=result.tokens_output,
            cost_estimate=result.cost_estimate,
            retry_count=result.retry_count,
            cache_hit=result.cache_hit,
            status=SectionStatus.COMPLETED if result.success else SectionStatus.FAILED,
            warnings=result.warnings,
            errors=[result.error] if result.error else [],
        )
        return output

    @staticmethod
    def _compute_delay(attempt: int, config: GenerationConfig) -> float:
        import random
        delay = config.base_delay * (config.backoff_multiplier ** attempt)
        delay = min(delay, config.max_delay)
        delay *= 0.5 + random.random() * 0.5
        return delay

    @staticmethod
    def _mock_generate(section_type: SectionType, prompt: SectionPrompt) -> str:
        heading = ""
        for line in prompt.user_prompt.split("\n"):
            if "HEADING:" in line:
                heading = line.split("HEADING:")[-1].strip()
                break

        lines = [
            f"This is a mock-generated {section_type.value} section.",
            "",
        ]
        if heading:
            lines.append(f"The section covers: {heading}.")
            lines.append("")

        lines.extend([
            "Here is the content for this section. It covers the key points",
            "mentioned in the outline and includes relevant information from",
            "the knowledge graph. The content is SEO-optimized and naturally",
            "incorporates target keywords.",
            "",
            "Key points covered in this section:",
            "- First important point about the topic",
            "- Second important point with supporting details",
            "- Third point that builds on previous information",
            "",
            "This section provides value to the reader by addressing their",
            "specific needs and questions about the topic at hand.",
        ])

        if section_type == SectionType.INTRODUCTION:
            return "\n".join([
                "Are you struggling with understanding this topic? You're not alone.",
                "",
                "In this comprehensive guide, we'll walk through everything you need",
                "to know about this subject. Whether you're a beginner or looking to",
                "deepen your understanding, this article has something for you.",
                "",
                "By the end of this guide, you'll have a clear understanding of the",
                "core concepts and be able to apply them in real-world scenarios.",
            ])

        if section_type == SectionType.FAQ:
            return "\n".join([
                "### What is this topic about?",
                "This topic covers the essential concepts and practices that help",
                "professionals achieve better results in their work.",
                "",
                "### Why is this important?",
                "Understanding this topic is crucial because it directly impacts",
                "productivity, quality, and outcomes in relevant fields.",
                "",
                "### How can I get started?",
                "Begin by understanding the fundamentals, then progressively build",
                "your knowledge through practice and real-world application.",
            ])

        if section_type == SectionType.CONCLUSION:
            return "\n".join([
                "In conclusion, mastering this topic requires understanding the core",
                "principles and applying them consistently. The key takeaways from",
                "this article will help you build a solid foundation.",
                "",
                "Remember to start with the basics and gradually work your way up",
                "to more advanced concepts. Practice and persistence are essential.",
            ])

        if section_type == SectionType.CTA:
            return "\n".join([
                "Ready to take your skills to the next level? Subscribe to our",
                "newsletter for more in-depth guides and tutorials on this topic.",
            ])

        return "\n".join(lines)


def generate_introduction_section(
    generator: SectionGenerator,
    context_manager: ContextManager,
) -> SectionOutput:
    ctx = context_manager.get_context_for_section(
        SectionType.INTRODUCTION,
        context_manager.get_intro_plan(),
        order=0,
    )
    return generator.generate(SectionType.INTRODUCTION, ctx)


def generate_body_section(
    generator: SectionGenerator,
    context_manager: ContextManager,
    section_plan: dict[str, Any],
    order: int,
    section_type: SectionType = SectionType.BODY,
) -> SectionOutput:
    ctx = context_manager.get_context_for_section(
        section_type,
        section_plan,
        order=order,
    )
    return generator.generate(section_type, ctx)


def generate_faq_section(
    generator: SectionGenerator,
    context_manager: ContextManager,
) -> SectionOutput:
    faq_plan_list = context_manager.get_faq_plan()
    faq_plan = faq_plan_list[0] if faq_plan_list else {}
    ctx = context_manager.get_context_for_section(
        SectionType.FAQ,
        faq_plan,
        order=999,
    )
    return generator.generate(SectionType.FAQ, ctx)


def generate_conclusion_section(
    generator: SectionGenerator,
    context_manager: ContextManager,
) -> SectionOutput:
    ctx = context_manager.get_context_for_section(
        SectionType.CONCLUSION,
        context_manager.get_summary_plan(),
        order=999,
    )
    return generator.generate(SectionType.CONCLUSION, ctx)


def generate_cta_section(
    generator: SectionGenerator,
    context_manager: ContextManager,
) -> SectionOutput:
    cta_plan_list = context_manager.get_cta_plan()
    cta_plan = cta_plan_list[0] if cta_plan_list else {}
    ctx = context_manager.get_context_for_section(
        SectionType.CTA,
        cta_plan,
        order=999,
    )
    return generator.generate(SectionType.CTA, ctx)
