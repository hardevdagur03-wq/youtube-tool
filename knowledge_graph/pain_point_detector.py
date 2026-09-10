"""Pain Point Detector — identifies problems, challenges, and obstacles.

Consumes analysis.json and transcript.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from knowledge_graph.knowledge_graph_models import PainPoint, Importance, Confidence

logger = logging.getLogger(__name__)

PAIN_POINT_PATTERNS = [
    r"(?:common|biggest|major|key|main|significant)\s+(?:problem|challenge|issue|pitfall|mistake|error|limitation|drawback|difficulty|obstacle|barrier|risk|concern)",
    r"(?:struggle|struggling|difficult|complicated|complex|hard|tough|painful|frustrating|annoying|problematic)",
    r"(?:unfortunately|however|but|yet|although|despite)\s+(?:many|most|some)\s+(?:people|developers|teams|companies|users)",
    r"(?:what doesn'?t|what not|fails|failure|break|broken|error|bug|issue)\s",
    r"(?:avoid|prevent|reduce|minimize|eliminate|mitigate)\s+(?:common|these|this|the)\s+(?:problem|issue|mistake|error|pitfall)",
]


class PainPointDetector:
    """Identifies pain points, problems, and challenges from transcript and analysis."""

    def detect(
        self,
        transcript: dict[str, Any] | None,
        analysis: dict[str, Any] | None,
    ) -> list[PainPoint]:
        pain_points: list[PainPoint] = []
        seen: set[str] = set()

        # From analysis
        if analysis and isinstance(analysis, dict):
            for field in ("pain_points", "challenges", "obstacles", "risks", "limitations"):
                items = analysis.get(field, [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str) and item.lower() not in seen:
                            seen.add(item.lower())
                            pain_points.append(PainPoint(
                                problem=item[:300],
                                severity=Importance.HIGH,
                                category=field,
                                evidence=f"from analysis.{field}",
                                confidence=Confidence.HIGH,
                            ))

        # From transcript
        if transcript and isinstance(transcript, dict):
            text = transcript.get("plain_text", "") or transcript.get("text", "")
            if isinstance(text, str) and text.strip():
                for pattern in PAIN_POINT_PATTERNS:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches[:5]:
                        match_str = match if isinstance(match, str) else str(match)
                        if match_str.lower() not in seen:
                            seen.add(match_str.lower())
                            pain_points.append(PainPoint(
                                problem=match_str[:300],
                                severity=Importance.MEDIUM,
                                category="extracted",
                                confidence=Confidence.LOW,
                            ))

        return pain_points
