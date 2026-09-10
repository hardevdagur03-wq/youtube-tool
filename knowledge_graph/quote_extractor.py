"""Quote Extractor — extracts meaningful quotes from transcript segments.

Consumes transcript.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from knowledge_graph.knowledge_graph_models import Quote, Importance, Confidence

logger = logging.getLogger(__name__)

QUOTE_PATTERNS = [
    re.compile(r'"([^"]{30,})"'),
    re.compile(r'\u201c([^\u201c]{30,})\u201d'),
    re.compile(r'\u2018([^\u2018]{30,})\u2019'),
    re.compile(r'\u00ab([^\u00ab]{30,})\u00bb'),
]

IMPORTANCE_KEYWORDS = [
    "important", "critical", "essential", "crucial", "key", "fundamental",
    "revolutionary", "game-changing", "breakthrough", "significant",
    "must", "should", "need to", "have to", "remember",
]

TOP_LEVEL_KEYWORDS = [
    "main", "primary", "core", "central", "most", "best", "greatest",
]


class QuoteExtractor:
    """Extracts meaningful quotes from transcript text."""

    def extract(self, transcript: dict[str, Any] | None) -> list[Quote]:
        quotes: list[Quote] = []
        seen: set[str] = set()

        if not transcript or not isinstance(transcript, dict):
            return quotes

        segments = transcript.get("segments", [])
        if not isinstance(segments, list):
            return quotes

        plain_text = transcript.get("plain_text", "") or transcript.get("text", "")
        if isinstance(plain_text, str) and plain_text.strip():
            for pattern in QUOTE_PATTERNS:
                for match in pattern.finditer(plain_text):
                    text = match.group(1).strip()
                    if text and len(text) > 20 and text.lower() not in seen:
                        seen.add(text.lower())
                        quotes.append(Quote(
                            text=text[:500],
                            importance=self._assess_importance(text),
                            confidence=Confidence.MEDIUM,
                        ))

        for i, segment in enumerate(segments):
            if not isinstance(segment, dict):
                continue
            text = segment.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue

            for pattern in QUOTE_PATTERNS:
                for match in pattern.finditer(text):
                    qtext = match.group(1).strip()
                    if qtext and len(qtext) > 20 and qtext.lower() not in seen:
                        seen.add(qtext.lower())
                        quotes.append(Quote(
                            text=qtext[:500],
                            source_timestamp=segment.get("start", 0.0),
                            context=text[:200],
                            importance=self._assess_importance(qtext),
                            confidence=Confidence.MEDIUM,
                            source_segment_index=i,
                        ))

        return quotes

    @staticmethod
    def _assess_importance(text: str) -> Importance:
        text_lower = text.lower()
        match_count = sum(1 for kw in IMPORTANCE_KEYWORDS if kw in text_lower)
        top_count = sum(1 for kw in TOP_LEVEL_KEYWORDS if kw in text_lower)
        if match_count >= 2 or top_count >= 1:
            return Importance.HIGH
        if match_count >= 1 or len(text) > 100:
            return Importance.MEDIUM
        return Importance.LOW
