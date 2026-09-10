"""Reading Time & Readability Estimator — estimates reading metrics.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import ReadingTimeInfo

logger = logging.getLogger(__name__)

WPM = 200


class ReadingTimeEstimator:
    """Estimates reading time and readability level."""

    def estimate(
        self,
        total_word_count: int,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> ReadingTimeInfo:
        info = ReadingTimeInfo()
        sp = seo_plan or {}
        analysis_data = analysis or {}

        total_seconds = (total_word_count / WPM) * 60
        info.minutes = int(total_seconds // 60)
        info.seconds = int(total_seconds % 60)

        if info.minutes < 3:
            info.reading_level = "beginner"
            info.complexity = "low"
            info.content_depth = "thin"
        elif info.minutes < 8:
            info.reading_level = "intermediate"
            info.complexity = "moderate"
            info.content_depth = "standard"
        elif info.minutes < 15:
            info.reading_level = "intermediate"
            info.complexity = "moderate"
            info.content_depth = "comprehensive"
        else:
            info.reading_level = "advanced"
            info.complexity = "high"
            info.content_depth = "ultimate"

        if isinstance(sp, dict):
            cs = sp.get("content_strategy", {})
            if isinstance(cs, dict):
                depth = cs.get("content_depth", "")
                if depth:
                    info.content_depth = depth

        if isinstance(analysis_data, dict):
            level = analysis_data.get("experience_level", "")
            if isinstance(level, str) and level:
                info.reading_level = level.lower()
                info.audience_match = 0.8

        return info
