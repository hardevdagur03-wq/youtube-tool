"""Statistics Extractor — extracts numbers, percentages, dates, and metrics.

Consumes transcript.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from knowledge_graph.knowledge_graph_models import (
    StatisticInfo,
    Confidence,
    Importance,
)

logger = logging.getLogger(__name__)

# Patterns for extracting statistics
STAT_PATTERNS = [
    (r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*%", "percentage"),
    (r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:dollars|USD|EUR|GBP)\b", "currency"),
    (r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:users|customers|people|developers|companies)", "count"),
    (r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:years|months|weeks|days|hours|minutes)", "duration"),
    (r"(?:over|more than|approximately|about|around)\s+(\d+(?:,\d{3})*(?:\.\d+)?)", "approximate"),
    (r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*x\s*(?:faster|better|more|higher|lower)", "multiplier"),
]


class StatisticsExtractor:
    """Extracts statistics, numbers, and metrics from transcript."""

    def extract(self, transcript: dict[str, Any] | None) -> list[StatisticInfo]:
        stats: list[StatisticInfo] = []
        seen: set[str] = set()

        if not transcript or not isinstance(transcript, dict):
            return stats

        text = transcript.get("plain_text", "") or transcript.get("text", "")
        if not isinstance(text, str) or not text.strip():
            return stats

        plain_text = text

        # Extract from analysis statistics
        analysis = transcript.get("statistics", None)
        if analysis and isinstance(analysis, dict):
            for key, value in analysis.items():
                if isinstance(value, (int, float)) and value > 0:
                    label = key.replace("_", " ").title()
                    stat_str = f"{value}"
                    if stat_str not in seen:
                        seen.add(stat_str)
                        stats.append(StatisticInfo(
                            value=str(value),
                            meaning=label,
                            category="video_statistics",
                            confidence=Confidence.HIGH,
                        ))

        # Pattern-based extraction from text
        for pattern, stat_type in STAT_PATTERNS:
            matches = re.findall(pattern, plain_text, re.IGNORECASE)
            for value_str in matches[:5]:
                if value_str not in seen:
                    seen.add(value_str)
                    stats.append(StatisticInfo(
                        value=value_str,
                        unit=stat_type,
                        category=f"extracted_{stat_type}",
                        confidence=Confidence.LOW,
                        importance=Importance.MEDIUM,
                    ))

        return stats
