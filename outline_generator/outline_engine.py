"""Outline Engine — orchestrates all outline planners.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from outline_generator.outline_models import (
    ContentOutline, OutlineMetadata, utc_now,
)
from outline_generator.title_engine import TitleEngine
from outline_generator.intro_planner import IntroPlanner
from outline_generator.problem_importance_planner import ProblemImportancePlanner
from outline_generator.heading_generator import HeadingGenerator
from outline_generator.section_planner import SectionPlanner
from outline_generator.table_planner import TablePlanner
from outline_generator.image_planner import ImagePlanner
from outline_generator.example_engine import ExampleEngine
from outline_generator.faq_planner import FAQPlanner
from outline_generator.cta_planner import CTAPlanner
from outline_generator.summary_planner import SummaryPlanner
from outline_generator.wordcount_estimator import WordCountEstimator
from outline_generator.readability_estimator import ReadingTimeEstimator
from outline_generator.outline_validator import OutlineValidator

logger = logging.getLogger(__name__)


class OutlineEngine:
    """Orchestrates all outline planning engines."""

    def __init__(self) -> None:
        self._title = TitleEngine()
        self._intro = IntroPlanner()
        self._problem = ProblemImportancePlanner()
        self._headings = HeadingGenerator()
        self._sections = SectionPlanner()
        self._tables = TablePlanner()
        self._images = ImagePlanner()
        self._examples = ExampleEngine()
        self._faqs = FAQPlanner()
        self._ctas = CTAPlanner()
        self._summary = SummaryPlanner()
        self._wordcount = WordCountEstimator()
        self._readability = ReadingTimeEstimator()
        self._validator = OutlineValidator()

    def build(
        self,
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        project_id: str = "",
        video_id: str = "",
    ) -> ContentOutline:
        start = time.time()
        outline = ContentOutline()
        kg = knowledge_graph or {}
        sp = seo_plan or {}
        analysis_data = analysis or {}

        try:
            # Derive primary keyword
            primary_keyword = ""
            if isinstance(sp, dict):
                ks = sp.get("keyword_strategy", {})
                if isinstance(ks, dict):
                    primary_keyword = ks.get("primary_keyword", "")
            if not primary_keyword and isinstance(analysis_data, dict):
                primary_keyword = analysis_data.get("primary_topic", "") or analysis_data.get("title", "")

            # Secondary keywords
            secondary_kws: list[str] = []
            if isinstance(sp, dict):
                ks = sp.get("keyword_strategy", {})
                if isinstance(ks, dict):
                    sk = ks.get("secondary_keywords", [])
                    if isinstance(sk, list):
                        secondary_kws = [s.get("keyword", "") if isinstance(s, dict) else str(s)
                                         for s in sk[:10]]

            # Target audience
            target_audience = ""
            if isinstance(sp, dict):
                ta = sp.get("target_audience", {})
                if isinstance(ta, dict):
                    target_audience = ta.get("primary_audience", "")

            # 1. Title
            outline.title = self._title.generate(primary_keyword, sp, analysis_data)

            # 2. Introduction plan
            outline.intro_plan = self._intro.plan(primary_keyword, target_audience, analysis_data, sp)

            # 3. Problem analysis
            outline.problem_analysis = self._problem.analyze(primary_keyword, kg, sp, analysis_data)

            # 4. Heading hierarchy
            sections = self._headings.generate(primary_keyword, secondary_kws, kg, sp)
            outline.sections = self._sections.enrich(sections, kg)

            # 5. Tables
            outline.tables = self._tables.recommend(primary_keyword, secondary_kws, sp)

            # 6. Images
            outline.images = self._images.recommend(primary_keyword, sp)

            # 7. Examples
            outline.examples = self._examples.plan(primary_keyword, kg, sp)

            # 8. FAQs
            outline.faqs = self._faqs.plan(primary_keyword, sp, kg)

            # 9. CTAs
            outline.ctas = self._ctas.plan(primary_keyword, sp)

            # 10. Summary
            outline.summary_plan = self._summary.plan(primary_keyword, kg, analysis_data)

            # 11. Word count
            outline.word_count_plan = self._wordcount.estimate(outline.sections, sp)

            # 12. Reading time
            outline.reading_time = self._readability.estimate(
                outline.word_count_plan.total_target, sp, analysis_data,
            )

            # 13. Validate
            issues = self._validator.validate(outline)
            outline.warnings = [i for i in issues if "weak" in i.lower() or "low" in i.lower()]
            outline.errors = [i for i in issues if "no" in i.lower() or "only" in i.lower() or "duplicate" in i.lower()]

            # Metadata
            quality = self._validator.compute_quality_score(outline)
            elapsed = (time.time() - start) * 1000
            outline.metadata = OutlineMetadata(
                version="1.0",
                created_at=utc_now(),
                project_id=project_id,
                video_id=video_id,
                source_artifacts=["knowledge_graph.json", "seo_plan.json", "analysis.json"],
                execution_time_ms=round(elapsed, 1),
                total_sections=len(outline.sections),
                total_tables=len(outline.tables),
                total_images=len(outline.images),
                quality_score=round(quality, 1),
            )

            logger.info(
                "Outline built: title='%s', sections=%d, tables=%d, images=%d, "
                "examples=%d, faqs=%d, words=%d, quality=%.1f, time=%.0fms",
                outline.title.primary_title, len(outline.sections),
                len(outline.tables), len(outline.images),
                len(outline.examples), len(outline.faqs),
                outline.word_count_plan.total_target, quality, elapsed,
            )

        except Exception as exc:
            logger.error("Outline build failed: %s", exc)
            outline.errors.append(f"Build failed: {exc}")

        return outline
