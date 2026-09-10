"""Intent Engine — determines search intent from analysis and knowledge graph.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import SearchIntent, SearchIntentType

logger = logging.getLogger(__name__)

INTENT_CLASSIFICATION: dict[str, SearchIntentType] = {
    "informational": SearchIntentType.INFORMATIONAL,
    "educational": SearchIntentType.EDUCATIONAL,
    "tutorial": SearchIntentType.TUTORIAL,
    "commercial": SearchIntentType.COMMERCIAL,
    "transactional": SearchIntentType.TRANSACTIONAL,
    "navigational": SearchIntentType.NAVIGATIONAL,
    "comparison": SearchIntentType.COMPARISON,
    "review": SearchIntentType.REVIEW,
    "how_to": SearchIntentType.TUTORIAL,
    "learn": SearchIntentType.EDUCATIONAL,
    "guide": SearchIntentType.EDUCATIONAL,
    "buy": SearchIntentType.TRANSACTIONAL,
    "best": SearchIntentType.COMMERCIAL,
    "top": SearchIntentType.COMMERCIAL,
    "vs": SearchIntentType.COMPARISON,
    "alternative": SearchIntentType.COMPARISON,
    "definition": SearchIntentType.INFORMATIONAL,
    "what_is": SearchIntentType.INFORMATIONAL,
}

FUNNEL_STAGES = {
    SearchIntentType.INFORMATIONAL: "awareness",
    SearchIntentType.EDUCATIONAL: "consideration",
    SearchIntentType.TUTORIAL: "consideration",
    SearchIntentType.COMMERCIAL: "consideration",
    SearchIntentType.COMPARISON: "decision",
    SearchIntentType.REVIEW: "decision",
    SearchIntentType.TRANSACTIONAL: "decision",
    SearchIntentType.NAVIGATIONAL: "decision",
}


class IntentEngine:
    """Determines search intent from analysis and content."""

    def determine(
        self,
        analysis: dict[str, Any] | None,
        primary_keyword: str = "",
    ) -> SearchIntent:
        intent = SearchIntent()
        analysis_data = analysis or {}

        if not isinstance(analysis_data, dict):
            return intent

        raw_intent = analysis_data.get("search_intent", "")
        if isinstance(raw_intent, str) and raw_intent:
            normalized = raw_intent.lower().strip()
            for key, intent_type in INTENT_CLASSIFICATION.items():
                if key in normalized or normalized in key:
                    intent.primary_intent = intent_type
                    intent.confidence = 0.8
                    intent.intent_evidence.append(f"Analysis indicates '{raw_intent}'")
                    break

        if intent.confidence < 0.8 and primary_keyword:
            pk_lower = primary_keyword.lower()
            for key, intent_type in INTENT_CLASSIFICATION.items():
                if key in pk_lower:
                    if intent.confidence < 0.6:
                        intent.primary_intent = intent_type
                        intent.confidence = 0.6
                        intent.intent_evidence.append(
                            f"Primary keyword '{primary_keyword}' suggests '{key}'"
                        )
                    else:
                        intent.secondary_intent.append(intent_type)
                    break

        if intent.confidence < 0.5:
            category = ""
            if isinstance(analysis_data, dict):
                category = analysis_data.get("content_category", "")
            if category:
                for key, intent_type in INTENT_CLASSIFICATION.items():
                    if key in category.lower():
                        intent.primary_intent = intent_type
                        intent.confidence = 0.5
                        intent.intent_evidence.append(
                            f"Content category '{category}' suggests '{key}'"
                        )
                        break

        intent.search_funnel_stage = FUNNEL_STAGES.get(
            intent.primary_intent, "awareness"
        )

        return intent
