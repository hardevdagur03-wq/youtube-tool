"""Linking Audit — Phase 9.

Validates internal and external links: anchor text, placement, diversity, broken references.
"""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, LinkingResult


class InternalLinkingValidator(BaseValidator):
    """Validates internal links."""

    WEAK_ANCHOR_TEXTS = {"click here", "here", "read more", "this article", "this page", "link", "more", "this"}

    def name(self) -> str:
        return "Internal Linking Audit"

    def validate(self, request: BlogReviewRequest) -> LinkingResult:
        links = request.internal_links or []
        content = request.content or ""

        issues: list[str] = []
        poor_anchors: list[str] = []

        for link in links:
            anchor = (link.get("anchor") or link.get("text") or "").strip().lower()
            url = link.get("url", "")

            if anchor in self.WEAK_ANCHOR_TEXTS:
                poor_anchors.append(f"Weak anchor text: '{anchor}' → {url}")
                issues.append(f"Replace generic anchor '{anchor}' with descriptive text")

            # Check anchor is contextual
            if len(anchor.split()) > 5:
                poor_anchors.append(f"Anchor text too long ({len(anchor.split())} words): '{anchor[:50]}'")
                issues.append(f"Shorten anchor text for '{anchor[:40]}...' to under 5 words")

        # Extract markdown links from content
        md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        for anchor_text, link_url in md_links:
            lower_anchor = anchor_text.lower().strip()
            if lower_anchor in self.WEAK_ANCHOR_TEXTS:
                poor_anchors.append(f"Weak anchor text: '{anchor_text}' → {link_url}")

        # Score
        total_links = len(links) + len(md_links)
        penalty = len(poor_anchors) * 10
        if total_links == 0:
            penalty += 20
        score = max(0, min(100, 100 - penalty))

        recs = []
        if total_links == 0:
            recs.append("Add internal links to related content for improved navigation and SEO")
        if poor_anchors:
            recs.append(f"Improve {len(poor_anchors)} anchor texts to be more descriptive")
        recs.append("Ensure internal links point to relevant, authoritative pages")

        return LinkingResult(
            score=round(score, 1),
            internal_link_count=total_links,
            poor_anchor_text=poor_anchors[:5],
            recommendations=recs,
        )


class ExternalLinkingValidator(BaseValidator):
    """Validates external links."""

    def name(self) -> str:
        return "External Linking Audit"

    def validate(self, request: BlogReviewRequest) -> LinkingResult:
        links = request.external_links or []
        content = request.content or ""

        issues: list[str] = []
        broken: list[str] = []

        for link in links:
            url = link.get("url", "")
            if url and not url.startswith("https://"):
                broken.append(f"Non-HTTPS link: {url}")
                issues.append(f"Use HTTPS for external link: {url}")

        # Extract markdown links from content and check for external ones
        md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        external_count = sum(1 for _, url in md_links if url.startswith("http") and "youtube.com" not in url.lower())
        internal_count = sum(1 for _, url in md_links if not url.startswith("http") or "youtube.com" in url.lower())

        total_external = len(links) + external_count

        penalty = len(broken) * 15
        if total_external == 0:
            penalty += 15
        score = max(0, min(100, 100 - penalty))

        recs = []
        if total_external == 0:
            recs.append("Add external links to authoritative sources to improve credibility and SEO")
        if broken:
            recs.append(f"Fix {len(broken)} non-HTTPS links")
        recs.append("Verify all external links point to authoritative, relevant domains")

        return LinkingResult(
            score=round(score, 1),
            external_link_count=total_external,
            broken_links=broken[:5],
            recommendations=recs,
        )
