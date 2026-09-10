"""Fact Extractor — extracts verifiable facts from transcript and analysis.

Consumes transcript.json and analysis.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from knowledge_graph.knowledge_graph_models import (
    FactInfo,
    Confidence,
    Importance,
)

logger = logging.getLogger(__name__)

FACT_PATTERNS = [
    r"(?:^|\.\s+)([A-Z][^.!?]*(?:is|are|was|were|has|have|had|means|refers|defines|represents|indicates|shows|demonstrates|proves|confirms|suggests|implies)[^.!?]*[.!?])",
    r"(?:^|\.\s+)([A-Z][^.!?]*(?:according to|studies show|research indicates|experts say|findings suggest)[^.!?]*[.!?])",
    r"(?:^|\.\s+)([A-Z][^.!?]*(?:important to note|key insight|fundamental|essential|crucial|critical)[^.!?]*[.!?])",
]


class FactExtractor:
    """Extracts verifiable facts from transcript and analysis."""

    def extract(
        self,
        transcript: dict[str, Any] | None,
        analysis: dict[str, Any] | None,
    ) -> list[FactInfo]:
        facts: list[FactInfo] = []
        seen: set[str] = set()

        # Extract from analysis summary
        if analysis and isinstance(analysis, dict):
            summary = analysis.get("summary", {})
            if isinstance(summary, dict):
                for field in ("key_insights", "bullet_points", "detailed", "executive"):
                    text = summary.get(field, "")
                    if isinstance(text, str) and text.strip():
                        if text.lower() not in seen:
                            seen.add(text.lower())
                            facts.append(FactInfo(
                                statement=text[:500],
                                category="insight",
                                importance=Importance.HIGH,
                                confidence=Confidence.MEDIUM,
                                context=f"from analysis summary: {field}",
                            ))
                    elif isinstance(text, list):
                        for item in text:
                            if isinstance(item, str) and item.strip() and item.lower() not in seen:
                                seen.add(item.lower())
                                facts.append(FactInfo(
                                    statement=item[:500],
                                    category="insight",
                                    importance=Importance.HIGH,
                                    confidence=Confidence.MEDIUM,
                                ))

            for field in ("key_takeaways", "learning_objectives", "main_solution", "business_value"):
                value = analysis.get(field, "")
                if isinstance(value, str) and value.strip() and value.lower() not in seen:
                    seen.add(value.lower())
                    facts.append(FactInfo(
                        statement=value[:500],
                        category="takeaway",
                        importance=Importance.MEDIUM,
                        confidence=Confidence.MEDIUM,
                    ))

        # Extract from transcript using patterns
        if transcript and isinstance(transcript, dict):
            segments = transcript.get("segments", [])
            if isinstance(segments, list):
                plain_text = transcript.get("plain_text", "") or transcript.get("text", "")
                if isinstance(plain_text, str):
                    for pattern in FACT_PATTERNS:
                        matches = re.findall(pattern, plain_text, re.MULTILINE)
                        for match in matches[:10]:
                            cleaned = match.strip()
                            if cleaned and len(cleaned) > 30 and cleaned.lower() not in seen:
                                seen.add(cleaned.lower())
                                facts.append(FactInfo(
                                    statement=cleaned[:500],
                                    confidence=Confidence.LOW,
                                    importance=Importance.MEDIUM,
                                    context="extracted from transcript",
                                ))

        return facts
