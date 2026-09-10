"""Timeline Builder — creates chronological timeline from transcript segments.

Consumes transcript.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from knowledge_graph.knowledge_graph_models import TimelineEvent, Importance, Confidence

logger = logging.getLogger(__name__)

TIME_PATTERNS = [
    r"(?:in|during|around|since|until|before|after)\s+(19|20)\d{2}",
    r"(?:in the|over the|during the)\s+(past|last|next|coming)\s+\d+\s+(year|years|decade|decades)",
    r"(?:early|late|mid)\s+(19|20)\d{2}s",
]


class TimelineBuilder:
    """Builds a chronological timeline from transcript segments."""

    def build(self, transcript: dict[str, Any] | None) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []
        seen: set[str] = set()

        if not transcript or not isinstance(transcript, dict):
            return events

        segments = transcript.get("segments", [])
        if not isinstance(segments, list):
            return events

        for i, segment in enumerate(segments):
            if not isinstance(segment, dict):
                continue
            text = segment.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue

            for pattern in TIME_PATTERNS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    ts = match.group(0)
                    if ts not in seen:
                        seen.add(ts)
                        segment_text = text[:200].strip()
                        if len(segment_text) > 30:
                            events.append(TimelineEvent(
                                event=f"Reference to {ts}",
                                description=segment_text,
                                importance=Importance.LOW,
                                confidence=Confidence.LOW,
                                source_segment_index=i,
                                timestamp=ts,
                            ))

            if i == 0:
                first_text = text[:200].strip()
                if len(first_text) > 20:
                    events.append(TimelineEvent(
                        event="Content begins",
                        description=first_text,
                        importance=Importance.MEDIUM,
                        confidence=Confidence.MEDIUM,
                        source_segment_index=i,
                    ))

        if events:
            events[-1].importance = Importance.HIGH

        return events
