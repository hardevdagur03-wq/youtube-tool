"""CTA Planner — plans calls to action for the outline.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import CTAInfo

logger = logging.getLogger(__name__)


class CTAPlanner:
    """Plans calls to action and engagement prompts."""

    def plan(
        self,
        primary_keyword: str,
        seo_plan: dict[str, Any] | None = None,
    ) -> list[CTAInfo]:
        ctas: list[CTAInfo] = []

        ctas.append(CTAInfo(
            type="primary",
            text=f"Start implementing {primary_keyword} today",
            placement_section="conclusion",
            intent="engagement",
            priority=9,
        ))

        ctas.append(CTAInfo(
            type="secondary",
            text="Subscribe for more in-depth guides",
            placement_section="conclusion",
            intent="newsletter",
            priority=7,
        ))

        ctas.append(CTAInfo(
            type="internal_navigation",
            text=f"Explore more resources on {primary_keyword}",
            placement_section="related_content",
            intent="exploration",
            priority=6,
        ))

        return ctas
