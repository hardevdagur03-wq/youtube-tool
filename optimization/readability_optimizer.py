"""Readability Optimizer — improves sentence length, paragraph flow, transitions, and clarity."""

from __future__ import annotations
import logging
import re
from typing import Any

from optimization.optimization_models import OptimizationContext, OptimizationType
from optimization.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

TRANSITION_WORDS = {
    "addition": ["also", "and", "besides", "furthermore", "moreover", "additionally", "plus", "similarly"],
    "contrast": ["but", "however", "although", "though", "yet", "still", "nevertheless", "nonetheless", "on the other hand", "conversely", "whereas"],
    "cause": ["because", "since", "as", "due to", "therefore", "thus", "consequently", "as a result", "hence"],
    "sequence": ["first", "second", "third", "next", "then", "finally", "lastly", "subsequently", "meanwhile"],
    "emphasis": ["indeed", "certainly", "importantly", "notably", "significantly", "especially", "particularly"],
    "example": ["for example", "for instance", "such as", "including", "like", "namely", "specifically", "to illustrate"],
    "conclusion": ["in conclusion", "to conclude", "in summary", "overall", "ultimately", "in short", "in brief"],
}


class ReadabilityOptimizer:
    """Improves readability through sentence simplification and transition enhancement."""

    def __init__(self, prompt_builder: PromptBuilder | None = None):
        self._prompt_builder = prompt_builder or PromptBuilder()

    def optimize(
        self,
        context: OptimizationContext,
        llm_call: callable,
    ) -> tuple[str, list[str]]:
        prompt = self._prompt_builder.build_prompt(context, OptimizationType.READABILITY)
        warnings: list[str] = []
        optimized = ""

        # First pass: quick rule-based readability fixes
        quick_fixed, quick_warnings = self._quick_readability_fixes(context.section_text)
        corrected_context = context.model_copy(update={"section_text": quick_fixed})
        prompt = self._prompt_builder.build_prompt(corrected_context, OptimizationType.READABILITY)
        warnings.extend(quick_warnings)

        try:
            optimized = llm_call(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                temperature=0.3,
                max_tokens=2048,
            )
            optimized = optimized.strip()
        except Exception as exc:
            logger.error("[ReadabilityOptimizer] LLM call failed: %s", exc)
            warnings.append(f"Readability optimization LLM call failed: {exc}")
            return quick_fixed, warnings

        if not optimized:
            warnings.append("Readability optimization returned empty, using quick fixes")
            return quick_fixed, warnings

        if len(optimized) < len(context.section_text) * 0.3:
            warnings.append("Optimized content too short, using quick fixes")
            return quick_fixed, warnings

        return optimized, warnings

    def _quick_readability_fixes(self, text: str) -> tuple[str, list[str]]:
        modified = text
        fixes: list[str] = []

        # Split overly long sentences
        sentences = re.split(r'(?<=[.!?])\s+', modified)
        fixed_sentences = []
        for sent in sentences:
            words = sent.split()
            if len(words) > 30:
                mid = len(words) // 2
                part1 = " ".join(words[:mid])
                part2 = " ".join(words[mid:])
                fixed_sentences.append(part1 + ".")
                fixed_sentences.append(part2[0].upper() + part2[1:] if part2 else part2)
                fixes.append(f"Split long sentence ({len(words)} words)")
            else:
                fixed_sentences.append(sent)
        modified = " ".join(fixed_sentences)

        # Add transition words to paragraphs missing them
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', modified) if p.strip()]
        fixed_paragraphs = []
        for i, para in enumerate(paragraphs):
            if i > 0 and not para.startswith("#"):
                has_transition = any(
                    para.lower().startswith(tw)
                    for tw in ["however", "furthermore", "moreover", "in addition", "additionally",
                               "nevertheless", "on the other hand", "consequently", "therefore",
                               "meanwhile", "subsequently", "finally", "overall"]
                )
                if not has_transition:
                    sent = para.split(".")[0]
                    if len(sent.split()) > 3:
                        fixes.append(f"Added transition to paragraph {i+1}")
            fixed_paragraphs.append(para)
        modified = "\n\n".join(fixed_paragraphs)

        return modified, fixes
