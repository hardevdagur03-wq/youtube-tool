"""Outline Validator — validates outline completeness and quality.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import ContentOutline

logger = logging.getLogger(__name__)

MIN_SECTIONS = 3


class OutlineValidator:
    """Validates outline structure, coverage, and quality."""

    def validate(self, outline: ContentOutline) -> list[str]:
        issues: list[str] = []

        if not outline.title.primary_title:
            issues.append("No primary title defined")

        if len(outline.sections) < MIN_SECTIONS:
            issues.append(f"Only {len(outline.sections)} sections (minimum {MIN_SECTIONS})")

        # Check for duplicate headings
        seen_headings: set[str] = set()
        for section in outline.sections:
            h_lower = section.heading.lower()
            if h_lower in seen_headings:
                issues.append(f"Duplicate heading: {section.heading}")
            seen_headings.add(h_lower)

        # Check heading hierarchy
        h2_count = sum(1 for s in outline.sections if s.heading_tag == "h2")
        if h2_count < 2:
            issues.append(f"Only {h2_count} H2 headings (recommend at least 3)")

        # Check weak sections
        for section in outline.sections:
            if not section.goal:
                issues.append(f"Section '{section.heading}' has no goal defined")
            if section.target_word_count < 100:
                issues.append(f"Section '{section.heading}' has low word count target ({section.target_word_count})")

        # Check coverage
        has_intro = any("intro" in s.heading.lower() or "what is" in s.heading.lower() for s in outline.sections)
        if not has_intro:
            issues.append("No introductory section found")

        has_conclusion = any("conclusion" in s.heading.lower() or "summary" in s.heading.lower() for s in outline.sections)
        if not has_conclusion:
            issues.append("No conclusion or summary section found")

        has_faq = any("faq" in s.heading.lower() or "question" in s.heading.lower() for s in outline.sections)
        if not has_faq and len(outline.faqs) == 0:
            issues.append("No FAQ section or items planned")

        if outline.word_count_plan.total_target < 300:
            issues.append("Total word count target too low")
        elif outline.word_count_plan.total_target > 10000:
            issues.append("Total word count target very high, consider splitting")

        if not outline.intro_plan.hook_approach:
            issues.append("No introduction hook approach defined")

        if not outline.ctas:
            issues.append("No calls to action planned")

        return issues

    def compute_quality_score(self, outline: ContentOutline) -> float:
        score = 0.0

        if outline.title.primary_title:
            score += 10
        if len(outline.sections) >= 5:
            score += 20
        elif len(outline.sections) >= 3:
            score += 10

        if outline.intro_plan.hook_approach:
            score += 5
        if outline.problem_analysis.primary_problem:
            score += 5
        if len(outline.tables) >= 1:
            score += 5
        if len(outline.images) >= 2:
            score += 5
        if len(outline.examples) >= 2:
            score += 10
        if len(outline.faqs) >= 3:
            score += 10
        if len(outline.ctas) >= 1:
            score += 5
        if outline.summary_plan.key_takeaways:
            score += 5

        has_h2 = any(s.heading_tag == "h2" for s in outline.sections)
        has_h3 = any(s.heading_tag == "h3" for s in outline.sections)
        if has_h2:
            score += 5
        if has_h3:
            score += 5

        if 800 <= outline.word_count_plan.total_target <= 5000:
            score += 5

        if outline.reading_time.minutes >= 3:
            score += 5

        return min(100.0, score)
