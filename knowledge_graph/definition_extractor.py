"""Definition Extractor — extracts terminology, definitions, and acronyms.

Consumes transcript.json and analysis.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from knowledge_graph.knowledge_graph_models import Definition, Confidence

logger = logging.getLogger(__name__)

DEFINITION_PATTERNS = [
    (r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:is|are|refers to|means|defines|represents|can be defined as)\s+([^.]{20,})\.", "explicit"),
    (r"(?:a|an)\s+([A-Z][a-z]+(?:\s+[a-zA-Z]+)*)\s+(?:is|can be)\s+(?:a|an)\s+([^.]{20,})\.", "implicit"),
    (r"(?:term|concept|called|known as|also known as)\s+[`\"]([^`\"]+)[`\"]", "named"),
    (r"([A-Z]{2,})\s*(?:stands for|is short for|is an acronym for|is an abbreviation for)\s+([^.]{20,})", "acronym"),
]

TECH_TERM_PATTERN = re.compile(
    r"\b([A-Z][a-z]*(?:JS|ML|AI|API|SDK|SQL|CSS|HTML|HTTP|JSON|XML|YAML|REST|CLI|IDE|DB|UI|UX|SEO|RAG|LLM))\b"
)


class DefinitionExtractor:
    """Extracts definitions, terminology, and acronyms."""

    def extract(
        self,
        transcript: dict[str, Any] | None,
        analysis: dict[str, Any] | None,
    ) -> list[Definition]:
        definitions: list[Definition] = []
        seen: set[str] = set()

        if not transcript or not isinstance(transcript, dict):
            return definitions

        text = transcript.get("plain_text", "") or transcript.get("text", "")
        if not isinstance(text, str) or not text.strip():
            return definitions

        for pattern, def_type in DEFINITION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                term = match[0].strip() if isinstance(match, tuple) else match
                if term.lower() not in seen:
                    seen.add(term.lower())
                    definition = match[1].strip() if isinstance(match, tuple) and len(match) > 1 else ""
                    definitions.append(Definition(
                        term=term[:100],
                        definition=definition[:500],
                        category=def_type,
                        confidence=Confidence.HIGH if def_type == "explicit" else Confidence.MEDIUM,
                    ))

        # Extract tech acronyms
        for match in TECH_TERM_PATTERN.finditer(text):
            term = match.group(1)
            if term.lower() not in seen:
                seen.add(term.lower())
                definitions.append(Definition(
                    term=term,
                    definition=f"{term} (technical term referenced in content)",
                    category="acronym",
                    difficulty="intermediate",
                    confidence=Confidence.LOW,
                ))

        return definitions
