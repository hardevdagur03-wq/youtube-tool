"""Heading Validation — Phase 9."""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, HeadingResult


class HeadingValidator(BaseValidator):
    """Validates heading hierarchy: single H1, proper nesting, no skipped levels."""

    def name(self) -> str:
        return "Heading Validation"

    def validate(self, request: BlogReviewRequest) -> HeadingResult:
        text = request.content
        if not text:
            return HeadingResult(score=100.0)

        hierarchy_issues: list[str] = []
        missing_headings: list[str] = []
        skipped_levels: list[str] = []

        # Extract all headings with their levels
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        headings = [(len(m.group(1)), m.group(2).strip()) for m in heading_pattern.finditer(text)]

        if not headings:
            hierarchy_issues.append("No headings found in document")
            return HeadingResult(
                score=0,
                h1_count=0,
                hierarchy_issues=hierarchy_issues,
                missing_headings=["H1 is required"],
                skipped_levels=[],
            )

        # Count H1s
        h1_count = sum(1 for level, _ in headings if level == 1)
        if h1_count == 0:
            hierarchy_issues.append("No H1 heading found — required for SEO")
            missing_headings.append("H1 heading")
        elif h1_count > 1:
            hierarchy_issues.append(f"Multiple H1 headings ({h1_count} found). Only one H1 is allowed.")
            for level, text_h in headings:
                if level == 1:
                    hierarchy_issues.append(f"  Extra H1: '{text_h[:60]}'")

        # Check hierarchy — no skipped levels
        if headings:
            first_level = headings[0][0]
            if first_level != 1 and h1_count == 0:
                hierarchy_issues.append(f"Document starts with H{first_level}, not H1")
                skipped_levels.append("H1")
            elif first_level > 2:
                hierarchy_issues.append(f"Document starts with H{first_level}, should start with H1 or H2")

        for i in range(1, len(headings)):
            prev_level = headings[i - 1][0]
            curr_level = headings[i][0]

            if curr_level > prev_level + 1:
                skipped = [f"H{prev_level + 1}"]
                skipped_levels.append(f"H{prev_level + 1}")
                hierarchy_issues.append(
                    f"Skipped heading level: H{prev_level} → H{curr_level}. "
                    f"Missing H{prev_level + 1} between '{headings[i - 1][1][:40]}' and '{headings[i][1][:40]}'"
                )

        # Check descriptive headings
        for level, text_h in headings:
            if len(text_h.split()) < 2:
                hierarchy_issues.append(f"H{level} heading too short (1 word): '{text_h}'")
            if len(text_h) > 100:
                hierarchy_issues.append(f"H{level} heading too long ({len(text_h)} chars): '{text_h[:60]}...'")

        # Check for generic/weak headings
        weak_headings = ["introduction", "conclusion", "overview", "summary", "details", "more", "other", "related"]
        for level, text_h in headings:
            lower_h = text_h.lower().strip().rstrip(':')
            if lower_h in weak_headings:
                hierarchy_issues.append(f"Weak generic H{level} heading: '{text_h}' — add more descriptive context")

        # Score calculation
        base = 100
        base -= (h1_count == 0) * 15
        base -= max(0, h1_count - 1) * 10
        base -= len(skipped_levels) * 10
        base -= len(hierarchy_issues) * 5
        score = max(0, min(100, base))

        return HeadingResult(
            score=round(score, 1),
            h1_count=h1_count,
            hierarchy_issues=hierarchy_issues,
            missing_headings=missing_headings,
            skipped_levels=skipped_levels,
        )
