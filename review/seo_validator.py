"""SEO Audit — Phase 9.

Validates keyword usage, meta data, heading structure, and SEO elements.
"""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest, SEOResult


class SEOValidator(BaseValidator):
    """Validates on-page SEO elements."""

    def name(self) -> str:
        return "SEO Audit"

    def validate(self, request: BlogReviewRequest) -> SEOResult:
        missing: list[str] = []
        recommendations: list[str] = []
        keyword = request.primary_keyword.lower() if request.primary_keyword else ""

        # Extract data from content
        content = request.content or ""
        meta_title = request.meta_title or request.blog_title or ""
        meta_desc = request.meta_description or ""

        # Title analysis
        title_len = len(request.blog_title) if request.blog_title else 0
        if not request.blog_title:
            missing.append("Blog title")
        elif title_len < 10:
            missing.append(f"Blog title too short ({title_len} chars, min 10)")

        # Meta title
        meta_title_len = len(meta_title)
        if not meta_title:
            missing.append("Meta title")
        elif meta_title_len < 30:
            missing.append(f"Meta title too short ({meta_title_len} chars, min 30)")
        elif meta_title_len > 60:
            missing.append(f"Meta title too long ({meta_title_len} chars, max 60)")

        # Meta description
        meta_desc_len = len(meta_desc)
        if not meta_desc:
            missing.append("Meta description")
        elif meta_desc_len < 120:
            missing.append(f"Meta description too short ({meta_desc_len} chars, min 120)")
        elif meta_desc_len > 160:
            missing.append(f"Meta description too long ({meta_desc_len} chars, max 160)")

        # Check H1
        h1s = re.findall(r'^#\s+(.+)$', content, re.MULTILINE)
        if not h1s:
            h1s = re.findall(r'#\s+(.+)$', content.split('\n')[0:2][0] if content.split('\n') else '', re.MULTILINE)

        # Check headings
        h2s = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
        h3s = re.findall(r'^###\s+(.+)$', content, re.MULTILINE)

        # Keyword presence checks (all explicit booleans)
        kw_in_title = bool(keyword) and request.blog_title is not None and keyword in request.blog_title.lower()
        kw_in_meta_title = bool(keyword) and keyword in meta_title.lower()
        kw_in_meta_desc = bool(keyword) and keyword in meta_desc.lower()
        kw_in_intro = False
        kw_in_h1 = False
        kw_in_h2 = False
        kw_in_conclusion = False

        # Check intro (first 200 words)
        intro_words = content.split()[:200]
        intro_text = ' '.join(intro_words)
        kw_in_intro = bool(keyword) and keyword in intro_text.lower()

        # Check H1
        kw_in_h1 = bool(keyword) and any(keyword in h.lower() for h in h1s)

        # Check H2s
        kw_in_h2 = bool(keyword) and any(keyword in h.lower() for h in h2s)

        # Check conclusion (last 200 words)
        conclusion_words = content.split()[-200:] if len(content.split()) > 200 else content.split()
        conclusion_text = ' '.join(conclusion_words)
        kw_in_conclusion = bool(keyword) and keyword in conclusion_text.lower()

        if not kw_in_title:
            missing.append("Primary keyword missing from title")
        if not kw_in_meta_title:
            missing.append("Primary keyword missing from meta title")
        if not kw_in_meta_desc:
            missing.append("Primary keyword missing from meta description")
        if not kw_in_intro:
            missing.append("Primary keyword missing from introduction")
        if not kw_in_h1:
            missing.append("Primary keyword missing from H1")
        if not h2s:
            missing.append("No H2 headings found")
        if not kw_in_h2:
            missing.append("Primary keyword missing from H2 headings")
        if not kw_in_conclusion:
            missing.append("Primary keyword missing from conclusion")

        # Check for heading hierarchy issues
        if h1s and len(h1s) > 1:
            missing.append(f"Multiple H1 headings ({len(h1s)} found). Use only one H1.")
        if not h1s:
            missing.append("No H1 heading found")

        # Keyword stuffing detection
        kw_count = 0
        stuffing = False
        if keyword:
            kw_count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', content.lower()))
            stuffing = bool(kw_count > (len(content.split()) * 0.03))

        # Secondary keyword check
        for sk in request.secondary_keywords:
            sk_lower = sk.lower()
            sk_count = len(re.findall(r'\b' + re.escape(sk_lower) + r'\b', content.lower()))
            if sk_count == 0:
                missing.append(f"Secondary keyword '{sk}' not found in content")

        # Image alt text check (Markdown images)
        images = re.findall(r'!\[([^\]]*)\]\([^)]+\)', content)
        missing_alt = [img for img in images if not img.strip()]
        if missing_alt:
            missing.append(f"{len(missing_alt)} images missing ALT text")

        # Internal/external links
        internal_links = len(request.internal_links) if request.internal_links else 0
        external_links = len(request.external_links) if request.external_links else 0

        if internal_links == 0:
            missing.append("No internal links found")
        if external_links == 0:
            recommendations.append("Consider adding external links to authoritative sources")

        # FAQ section check
        if not request.faq or len(request.faq) == 0:
            recommendations.append("Add an FAQ section for rich snippet eligibility")

        # Calculate score
        base_score = 100
        base_score -= len(missing) * 8
        if stuffing:
            base_score -= 15
        if meta_title_len < 30 or meta_title_len > 60:
            base_score -= 5
        if meta_desc_len < 120 or meta_desc_len > 160:
            base_score -= 5
        score = max(0, min(100, base_score))

        return SEOResult(
            score=round(score, 1),
            title_length=title_len,
            meta_title_length=meta_title_len,
            meta_description_length=meta_desc_len,
            primary_keyword_in_title=kw_in_title,
            primary_keyword_in_meta_title=kw_in_meta_title,
            primary_keyword_in_meta_description=kw_in_meta_desc,
            primary_keyword_in_introduction=kw_in_intro,
            primary_keyword_in_h1=kw_in_h1,
            primary_keyword_in_h2=kw_in_h2,
            primary_keyword_in_conclusion=kw_in_conclusion,
            keyword_stuffing_detected=stuffing,
            missing_elements=missing,
            recommendations=recommendations,
        )
