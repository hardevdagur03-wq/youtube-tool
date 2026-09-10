"""Accessibility Review — Phase 9.

Validates image ALT text, heading structure, table accessibility, link clarity.
"""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, AccessibilityResult


class AccessibilityValidator(BaseValidator):
    """Validates content accessibility."""

    def name(self) -> str:
        return "Accessibility Review"

    def validate(self, request: BlogReviewRequest) -> AccessibilityResult:
        text = request.content
        if not text:
            return AccessibilityResult(score=100.0)

        link_issues: list[str] = []
        heading_issues: list[str] = []
        recommendations: list[str] = []

        # Check images for ALT text
        images = re.findall(r'!\[([^\]]*)\]\([^)]+\)', text)
        missing_alt = [img for img in images if not img.strip()]
        images_with_alt = [img for img in images if img.strip()]

        if missing_alt:
            recommendations.append(f"Add ALT text to {len(missing_alt)} images")
        if images_with_alt:
            # Check for generic ALT text
            generic_alt = {"image", "photo", "picture", "screenshot", "diagram", "graph", "img", "image1", "pic"}
            for alt in images_with_alt:
                if alt.lower().strip() in generic_alt:
                    link_issues.append(f"Generic ALT text: '{alt}' — use descriptive text")

        # Check heading structure
        headings = re.findall(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE)
        prev_level = 0
        for level, heading_text in headings:
            level_num = len(level)
            if prev_level and level_num > prev_level + 1:
                heading_issues.append(
                    f"Skipped heading level: H{prev_level} → H{level_num} for '{heading_text[:50]}'"
                )
            prev_level = level_num

        # Check link text clarity (Markdown links)
        links = re.findall(r'\[([^\]]+)\]\([^)]+\)', text)
        weak_anchors = {"click here", "here", "read more", "this", "link", "more", "go", "this page"}
        for anchor in links:
            lower = anchor.lower().strip()
            if lower in weak_anchors:
                link_issues.append(f"Non-descriptive link text: '{anchor}' — use descriptive text")

        # Check for empty links
        empty_links = re.findall(r'\[\]\([^)]+\)', text)
        if empty_links:
            link_issues.append(f"{len(empty_links)} empty/missing link text found")

        # Check table accessibility (Markdown tables)
        tables = re.findall(r'^\|.+\|\n\|[-| ]+\|\n(?:\|.+\|\n?)*', text, re.MULTILINE)
        for table in tables:
            lines = table.strip().split('\n')
            if len(lines) < 2:
                continue
            header = lines[0]
            # Check if header row is clear
            header_cells = [c.strip() for c in header.strip('|').split('|')]
            empty_headers = [c for c in header_cells if not c]
            if empty_headers:
                link_issues.append("Table has empty header cells — all columns should have headers")

        # Check list formatting
        lists = re.findall(r'(?:^[*-]\s.+$(?:\n[*-]\s.+$)*)', text, re.MULTILINE)
        for lst in lists:
            items = re.findall(r'^[*-]\s(.+)$', lst, re.MULTILINE)
            for item in items:
                if len(item.strip()) > 200:
                    link_issues.append(f"List item too long ({len(item.strip())} chars) — consider breaking into paragraphs")
                    break

        # Check code blocks for language specification
        code_blocks = re.findall(r'```(\w*)\n', text)
        for i, lang in enumerate(code_blocks):
            if not lang.strip():
                link_issues.append(f"Code block {i + 1} missing language specification — add for syntax highlighting")

        # Calculate score
        issues_count = len(link_issues) + len(heading_issues)
        penalty = issues_count * 5 + len(missing_alt) * 10
        score = max(0, min(100, 100 - penalty))

        return AccessibilityResult(
            score=round(score, 1),
            images_missing_alt=len(missing_alt),
            heading_structure_issues=heading_issues,
            link_text_issues=link_issues,
            recommendations=recommendations,
        )
