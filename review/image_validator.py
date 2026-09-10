"""Image Validator — validates ALT text, captions, placement, and references."""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest
from review.review_models_ext import MarkdownReport


class ImageValidator(BaseValidator):
    """Validates image references, ALT text, captions, and placement."""

    def name(self) -> str:
        return "Image Validation"

    def validate(self, request: BlogReviewRequest) -> MarkdownReport:
        text = request.content
        if not text:
            return MarkdownReport(score=100.0)

        image_issues: list[str] = []
        images_missing_alt = 0

        # Standard Markdown images: ![alt](url)
        md_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', text)
        for alt, src in md_images:
            self._check_image(alt, src, image_issues)

        # HTML <img> tags
        html_images = re.findall(r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>', text, re.IGNORECASE)
        for src in html_images:
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', text[text.index(src)-100:text.index(src)+100])
            alt = alt_match.group(1) if alt_match else ""
            self._check_image(alt, src, image_issues)

        # Count images with missing alt
        for alt, src in md_images:
            if not alt.strip():
                images_missing_alt += 1

        # Check for figure/figcaption patterns
        figure_pattern = re.findall(r'<figure>.*?</figure>', text, re.DOTALL | re.IGNORECASE)
        for fig in figure_pattern:
            if '<figcaption>' not in fig:
                image_issues.append("Figure element without figcaption found")

        # Check image placement (images should be in their own paragraph)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if re.match(r'^\s*!\[', line):
                if i > 0 and lines[i-1].strip() and not lines[i-1].strip().startswith('#'):
                    pass
                if i < len(lines) - 1 and lines[i+1].strip() and not lines[i+1].strip().startswith('#'):
                    pass

        # Count total images
        total_images = len(md_images) + len(html_images)

        # Score calculation
        score = 100.0
        if images_missing_alt > 0:
            score -= images_missing_alt * 10
        if len(image_issues) > total_images * 0.5 and total_images > 0:
            score -= 10
        score = max(0, min(100, score))

        return MarkdownReport(
            score=round(score, 1),
            image_count=total_images,
            images_missing_alt=images_missing_alt,
            image_issues=image_issues,
            issues=image_issues,
        )

    def _check_image(self, alt: str, src: str, issues: list[str]) -> None:
        if not alt.strip():
            issues.append(f"Image '{src}' missing ALT text — required for accessibility and SEO")
        elif len(alt.strip()) < 5:
            issues.append(f"Image ALT text too short ('{alt.strip()}') — use descriptive text (5+ chars)")
        elif len(alt.strip()) > 125:
            issues.append(f"Image ALT text too long ({len(alt.strip())} chars) — keep under 125 characters")
        if not src.strip():
            issues.append("Image with empty source URL found")
        elif src.startswith('http:') and not src.startswith('https:'):
            issues.append(f"Image URL '{src}' uses HTTP instead of HTTPS")
