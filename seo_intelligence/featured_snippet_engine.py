"""Featured Snippet Engine — generates featured snippet optimization strategy.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import FeaturedSnippetPlan

logger = logging.getLogger(__name__)


class FeaturedSnippetEngine:
    """Generates featured snippet targeting strategy."""

    def generate(
        self,
        primary_keyword: str = "",
        faq_questions: list[str] | None = None,
        definitions: list[dict] | None = None,
    ) -> list[FeaturedSnippetPlan]:
        snippets: list[FeaturedSnippetPlan] = []
        seen: set[str] = set()

        # Paragraph snippet for primary keyword definition
        if primary_keyword:
            snippets.append(FeaturedSnippetPlan(
                target_question=f"What is {primary_keyword}?",
                target_section="introduction",
                recommended_format="paragraph",
                keyword=primary_keyword,
                optimization_tips=[
                    "Place definition in first 100 words",
                    "Use bold for the term being defined",
                    "Keep paragraph to 40-60 words",
                ],
                priority=10,
            ))
            seen.add(f"What is {primary_keyword}?")

        # List snippets from definitions
        if definitions:
            for d in definitions[:3]:
                if isinstance(d, dict):
                    term = d.get("term", "")
                    question = f"What is {term}?"
                    if question not in seen and term:
                        seen.add(question)
                        snippets.append(FeaturedSnippetPlan(
                            target_question=question,
                            target_section="definitions",
                            recommended_format="paragraph",
                            keyword=term,
                            priority=7,
                        ))

        # FAQ-based snippets
        if faq_questions:
            for q in faq_questions[:5]:
                if q not in seen:
                    seen.add(q)
                    fmt = "paragraph"
                    if q.lower().startswith(("how", "what are", "what is", "which")):
                        fmt = "list"
                    snippets.append(FeaturedSnippetPlan(
                        target_question=q,
                        target_section="faq",
                        recommended_format=fmt,
                        keyword=primary_keyword,
                        priority=6,
                    ))

        return snippets
