"""Hallucination Corrector — cross-checks content against knowledge graph, removes unsupported claims."""

from __future__ import annotations
import logging
import re
from typing import Any

from optimization.optimization_models import OptimizationContext, OptimizationType
from optimization.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


HALLUCINATION_PATTERNS = [
    (r'\baccording to a \d{4} study\b', "unverifiable study reference"),
    (r'\ba \d{4} (study|report|survey|analysis) (by|from|published)\b', "unverifiable research reference"),
    (r'\bresearch (shows|suggests|indicates|proves|demonstrates)\b', "unsupported research claim"),
    (r'\bstudies show\b', "unsupported studies claim"),
    (r'\bexperts (say|agree|believe|suggest|recommend)\b', "unsupported expert opinion"),
    (r'\bmany (studies|experts|researchers) (have shown|believe|suggest|agree)\b', "unsupported consensus claim"),
    (r'\bit is (widely|generally|well) (known|accepted|understood|recognized) that\b', "unsupported general knowledge claim"),
    (r'\baccording to industry (experts|analysts|sources)\b', "unsupported industry claim"),
]


class HallucinationCorrector:
    """Detects and corrects hallucinated content by cross-referencing against knowledge graph."""

    def __init__(self, prompt_builder: PromptBuilder | None = None):
        self._prompt_builder = prompt_builder or PromptBuilder()

    def optimize(
        self,
        context: OptimizationContext,
        llm_call: callable,
    ) -> tuple[str, list[str]]:
        warnings: list[str] = []

        # First pass: pattern-based detection
        detected, pattern_warnings = self._detect_hallucinations(context.section_text, context.knowledge_graph)
        warnings.extend(pattern_warnings)

        if not detected:
            logger.debug("[HallucinationCorrector] No pattern-based hallucinations detected")
            return context.section_text, warnings

        # Build context with knowledge graph facts
        kg_facts = self._extract_kg_facts(context.knowledge_graph)
        enriched_context = context.model_copy(update={
            "review_findings": context.review_findings + [
                {"description": f"Hallucination pattern detected: {d}", "location": "section"}
                for d in detected[:5]
            ],
        })

        prompt = self._prompt_builder.build_prompt(enriched_context, OptimizationType.HALLUCINATION)
        optimized = ""

        try:
            optimized = llm_call(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                temperature=0.2,
                max_tokens=2048,
            )
            optimized = optimized.strip()
        except Exception as exc:
            logger.error("[HallucinationCorrector] LLM call failed: %s", exc)
            warnings.append(f"Hallucination correction LLM call failed: {exc}")
            return context.section_text, warnings

        if not optimized:
            warnings.append("Hallucination correction returned empty, using original")
            return context.section_text, warnings

        return optimized, warnings

    def _detect_hallucinations(self, text: str, knowledge_graph: Any) -> tuple[list[str], list[str]]:
        detected: list[str] = []
        warnings: list[str] = []
        text_lower = text.lower()

        for pattern, description in HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                detected.append(f"{description}: '{match}'")
                warnings.append(f"Potential hallucination: {description} ('{match}')")

        # Check statistics against knowledge graph
        if isinstance(knowledge_graph, dict):
            kg_stats = knowledge_graph.get("statistics", []) if isinstance(knowledge_graph, dict) else []
            verified_values = set()
            for stat in kg_stats:
                if isinstance(stat, dict):
                    val = stat.get("value", "") or stat.get("statistic", "")
                    if val:
                        verified_values.add(str(val).lower())

            # Find percentage claims not in KG
            pct_claims = re.findall(r'\b\d+%\'?\s*(of|increase|decrease|improvement|reduction)', text_lower)
            for claim in pct_claims:
                if claim.lower() not in verified_values:
                    detected.append(f"Unverified percentage claim: '{claim}'")
                    warnings.append(f"Unverified statistic: '{claim}' not found in knowledge graph")

        return detected, warnings

    def _extract_kg_facts(self, knowledge_graph: Any) -> list[str]:
        facts: list[str] = []
        if not isinstance(knowledge_graph, dict):
            return facts

        kg_facts = knowledge_graph.get("facts", []) if isinstance(knowledge_graph, dict) else []
        for fact in kg_facts:
            if isinstance(fact, dict):
                statement = fact.get("statement", fact.get("fact", ""))
                if statement:
                    facts.append(statement)

        kg_stats = knowledge_graph.get("statistics", []) if isinstance(knowledge_graph, dict) else []
        for stat in kg_stats:
            if isinstance(stat, dict):
                value = stat.get("value", stat.get("statistic", ""))
                context = stat.get("context", stat.get("description", ""))
                if value:
                    facts.append(f"Statistic: {value} - {context}" if context else f"Statistic: {value}")

        return facts[:10]
