"""Content Completeness — Phase 9.

Validates that blog covers all required sections for the given search intent.
"""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, CompletenessResult


class CompletenessValidator(BaseValidator):
    """Checks whether the blog fully answers user intent."""

    def name(self) -> str:
        return "Content Completeness"

    def validate(self, request: BlogReviewRequest) -> CompletenessResult:
        text = request.content
        if not text:
            return CompletenessResult(
                score=0,
                missing_sections=["All content sections are missing"],
            )

        missing_sections: list[str] = []
        suggested_topics: list[str] = []

        # Check introduction (first ~10% of content)
        intro_text = text[:500].lower()
        has_intro = bool(
            re.search(r'\bintroduction\b', intro_text, re.IGNORECASE)
            or text.startswith('# ')
            or len(text.split()[:50]) > 10
        )
        if not has_intro:
            missing_sections.append("Clear introduction")

        # Check core explanation
        body_length = len(text.split())
        has_core = body_length > 200
        if not has_core:
            missing_sections.append("Core content / body")

        # Check examples
        has_examples = bool(
            re.search(r'\b(for example|for instance|such as|e\.g\.|like)\b', text, re.IGNORECASE)
        )
        if not has_examples:
            missing_sections.append("Examples or illustrations")
            suggested_topics.append("Add concrete examples to illustrate key points")

        # Check best practices
        has_best_practices = bool(
            re.search(r'\b(best practice|best practice|recommend|should|ensure|avoid|tip)\b', text, re.IGNORECASE)
        )
        if not has_best_practices:
            missing_sections.append("Best practices or recommendations")

        # Check benefits discussion
        has_benefits = bool(
            re.search(r'\b(benefit|advantage|pros|value|important|key|essential)\b', text, re.IGNORECASE)
        )
        if not has_benefits:
            missing_sections.append("Benefits or value proposition")

        # Check limitations
        has_limitations = bool(
            re.search(r'\b(limitation|caveat|drawback|disadvantage|cons|challenge|trade-off|however|but|although)\b', text, re.IGNORECASE)
        )
        if not has_limitations:
            missing_sections.append("Limitations or caveats")
            suggested_topics.append("Acknowledge limitations or edge cases for balanced coverage")

        # Check FAQ
        has_faq = bool(request.faq and len(request.faq) > 0) or bool(re.search(r'^##?\s*FAQ|frequently asked', text, re.MULTILINE | re.IGNORECASE))
        if not has_faq:
            missing_sections.append("FAQ section")

        # Check summary/conclusion
        has_summary = bool(
            re.search(r'\b(in conclusion|to summarize|in summary|overall|wrapping up|final thoughts)\b', text, re.IGNORECASE)
            or bool(re.search(r'^##?\s*conclusion', text, re.MULTILINE | re.IGNORECASE))
        )
        if not has_summary:
            missing_sections.append("Summary or conclusion")

        # Check CTA
        has_cta = bool(
            re.search(r'\b(get started|sign up|learn more|subscribe|try|download|contact|register|start|begin)\b', text[-500:].lower())
        )
        if not has_cta:
            missing_sections.append("Call-to-action")
            suggested_topics.append("Add a relevant call-to-action based on content type and audience")

        # Calculate score
        present_count = sum([has_intro, has_core, has_examples, has_best_practices,
                            has_benefits, has_limitations, has_faq, has_summary, has_cta])
        score = (present_count / 9) * 100

        # Intent-specific suggestions
        intent = (request.search_intent or "").lower()
        if "tutorial" in intent or "how" in intent:
            if not re.search(r'\b(step|steps|step-by-step)\b', text, re.IGNORECASE):
                suggested_topics.append("Add step-by-step instructions for tutorial content")
        if "comparative" in intent or "vs" in intent:
            if not re.search(r'\b(comparison|compare|versus|vs\.|difference)\b', text, re.IGNORECASE):
                suggested_topics.append("Add direct comparison table or analysis for this comparison content")

        return CompletenessResult(
            score=round(score, 1),
            has_introduction=has_intro,
            has_core_explanation=has_core,
            has_examples=has_examples,
            has_best_practices=has_best_practices,
            has_benefits=has_benefits,
            has_limitations=has_limitations,
            has_faq=has_faq,
            has_summary=has_summary,
            has_call_to_action=has_cta,
            missing_sections=missing_sections,
            suggested_topics=suggested_topics,
        )
