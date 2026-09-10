"""SEO Engine — orchestrates all SEO intelligence engines.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from seo_intelligence.seo_models import (
    SEOPlan, KeywordStrategy, SearchIntent, TargetAudience,
    URLInfo, MetaInfo, HeadingStrategy, ContentStrategy,
    PlanMetadata, SEOScore, utc_now,
)
from seo_intelligence.keyword_engine import KeywordEngine
from seo_intelligence.intent_engine import IntentEngine
from seo_intelligence.audience_engine import AudienceEngine
from seo_intelligence.url_generator import URLGenerator
from seo_intelligence.meta_generator import MetaGenerator
from seo_intelligence.heading_strategy_engine import HeadingStrategyEngine
from seo_intelligence.faq_engine import FAQEngine
from seo_intelligence.schema_engine import SchemaEngine
from seo_intelligence.featured_snippet_engine import FeaturedSnippetEngine
from seo_intelligence.competitor_strategy_engine import CompetitorStrategyEngine
from seo_intelligence.internal_link_engine import InternalLinkEngine
from seo_intelligence.external_link_engine import ExternalLinkEngine
from seo_intelligence.seo_scoring import SEOScoring
from seo_intelligence.seo_validator import SEOValidator

logger = logging.getLogger(__name__)


class SEOEngine:
    """Orchestrates all SEO intelligence engines."""

    def __init__(self) -> None:
        self._keyword = KeywordEngine()
        self._intent = IntentEngine()
        self._audience = AudienceEngine()
        self._url = URLGenerator()
        self._meta = MetaGenerator()
        self._headings = HeadingStrategyEngine()
        self._faq = FAQEngine()
        self._schema = SchemaEngine()
        self._snippet = FeaturedSnippetEngine()
        self._competitor = CompetitorStrategyEngine()
        self._internal_links = InternalLinkEngine()
        self._external_links = ExternalLinkEngine()
        self._scoring = SEOScoring()
        self._validator = SEOValidator()

    def build(
        self,
        knowledge_graph: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        project_id: str = "",
        video_id: str = "",
    ) -> SEOPlan:
        start = time.time()
        plan = SEOPlan()
        kg = knowledge_graph or {}
        analysis_data = analysis or {}

        try:
            # 1. Keyword strategy
            keyword_strategy = self._keyword.generate(kg, analysis_data)
            plan.keyword_strategy = keyword_strategy
            primary_keyword = keyword_strategy.primary_keyword
            secondary_kws = [k.keyword for k in keyword_strategy.secondary_keywords]
            all_question_kws = keyword_strategy.question_keywords

            # 2. Search intent
            plan.search_intent = self._intent.determine(analysis_data, primary_keyword)

            # 3. Target audience
            plan.target_audience = self._audience.identify(analysis_data, kg)

            # 4. URL
            title = ""
            if isinstance(analysis_data, dict):
                title = analysis_data.get("primary_topic", "") or analysis_data.get("title", "")
            plan.url = self._url.generate(primary_keyword, title)

            # 5. Meta
            plan.meta = self._meta.generate(
                primary_keyword,
                plan.search_intent.primary_intent,
                plan.target_audience.primary_audience,
                analysis_data,
            )

            # 6. Heading strategy + content strategy
            heading_strategy, content_strategy = self._headings.generate(
                primary_keyword, secondary_kws, kg,
            )
            plan.heading_strategy = heading_strategy
            plan.content_strategy = content_strategy

            # 7. FAQ
            definitions = kg.get("definitions", []) if isinstance(kg, dict) else []
            plan.faqs = self._faq.generate(kg, primary_keyword)

            # 8. Schema
            plan.schemas = self._schema.generate(
                primary_keyword, plan.meta.meta_title,
                plan.meta.meta_description, analysis_data,
            )

            # 9. Featured snippets
            faq_questions = [f.question for f in plan.faqs]
            plan.featured_snippets = self._snippet.generate(
                primary_keyword, faq_questions, definitions,
            )

            # 10. Competitor strategy
            plan.competitor_strategy = self._competitor.generate(
                primary_keyword, kg, analysis_data,
            )

            # 11. Internal links
            plan.internal_links = self._internal_links.generate(kg, primary_keyword)

            # 12. External links
            plan.external_links = self._external_links.generate(kg, primary_keyword)

            # 13. SEO scores
            plan.scores = self._scoring.compute(keyword_strategy, content_strategy)

            # 14. Validate
            issues = self._validator.validate(plan)
            plan.warnings = [i for i in issues if "duplicate" in i.lower() or "short" in i.lower() or "long" in i.lower()]
            plan.errors = [i for i in issues if "no" in i.lower() or "missing" in i.lower()]

            # Metadata
            elapsed = (time.time() - start) * 1000
            plan.metadata = PlanMetadata(
                version="1.0",
                created_at=utc_now(),
                project_id=project_id,
                video_id=video_id,
                source_artifacts=["knowledge_graph.json", "analysis.json"],
                execution_time_ms=round(elapsed, 1),
            )

            logger.info(
                "SEO plan built: primary='%s', keywords=%d, schemas=%d, faqs=%d, score=%.1f, time=%.0fms",
                primary_keyword, keyword_strategy.total_keyword_count,
                len(plan.schemas), len(plan.faqs),
                plan.scores.overall_score, elapsed,
            )

        except Exception as exc:
            logger.error("SEO plan build failed: %s", exc)
            plan.errors.append(f"Build failed: {exc}")

        return plan
