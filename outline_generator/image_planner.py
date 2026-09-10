"""Image Planner — recommends visual elements for the content outline.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import ImageRecommendation

logger = logging.getLogger(__name__)


class ImagePlanner:
    """Recommends images, diagrams, and visual elements."""

    def recommend(
        self,
        primary_keyword: str,
        seo_plan: dict[str, Any] | None = None,
    ) -> list[ImageRecommendation]:
        images: list[ImageRecommendation] = []
        sp = seo_plan or {}

        depth = "comprehensive"
        if isinstance(sp, dict):
            cs = sp.get("content_strategy", {})
            if isinstance(cs, dict):
                depth = cs.get("content_depth", "comprehensive")

        images.append(ImageRecommendation(
            type="hero_image",
            purpose="Visual introduction to the topic",
            placement_section="introduction",
            alt_text_suggestion=f"{primary_keyword} overview illustration",
            priority=9,
            description=f"Hero image representing {primary_keyword}",
        ))

        images.append(ImageRecommendation(
            type="diagram",
            purpose="Explain the core concept visually",
            placement_section="overview",
            alt_text_suggestion=f"{primary_keyword} architecture or workflow diagram",
            priority=8,
            description=f"Diagram showing how {primary_keyword} works",
        ))

        if depth in ("comprehensive", "ultimate"):
            images.append(ImageRecommendation(
                type="infographic",
                purpose="Summarize key statistics and data points",
                placement_section="statistics",
                alt_text_suggestion=f"{primary_keyword} key statistics infographic",
                priority=7,
                description=f"Infographic with key {primary_keyword} metrics",
            ))

            images.append(ImageRecommendation(
                type="screenshot",
                purpose="Show real implementation example",
                placement_section="implementation",
                alt_text_suggestion=f"{primary_keyword} implementation screenshot",
                priority=6,
                description=f"Screenshot demonstrating {primary_keyword} in action",
            ))

        if depth == "ultimate":
            images.append(ImageRecommendation(
                type="comparison_chart",
                purpose="Visual comparison of options",
                placement_section="comparison",
                alt_text_suggestion=f"{primary_keyword} comparison chart",
                priority=6,
                description=f"Chart comparing different {primary_keyword} approaches",
            ))

        return images
