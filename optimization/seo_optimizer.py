"""SEO Optimizer — improves keyword placement, semantic coverage, heading optimization, and search intent alignment."""

from __future__ import annotations
import logging
import re
from typing import Any

from optimization.optimization_models import OptimizationContext, OptimizationType
from optimization.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class SEOOptimizer:
    """Targeted SEO content optimization."""

    def __init__(self, prompt_builder: PromptBuilder | None = None):
        self._prompt_builder = prompt_builder or PromptBuilder()

    def optimize(
        self,
        context: OptimizationContext,
        llm_call: callable,
    ) -> tuple[str, list[str]]:
        prompt = self._prompt_builder.build_prompt(context, OptimizationType.SEO)
        warnings: list[str] = []
        optimized = ""

        try:
            optimized = llm_call(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                temperature=0.3,
                max_tokens=2048,
            )
            optimized = optimized.strip()
        except Exception as exc:
            logger.error("[SEOOptimizer] LLM call failed: %s", exc)
            warnings.append(f"SEO optimization LLM call failed: {exc}")
            return context.section_text, warnings

        if not optimized:
            warnings.append("SEO optimization returned empty content, using original")
            return context.section_text, warnings

        # Verify keyword presence
        if context.primary_keyword:
            kw_lower = context.primary_keyword.lower()
            orig_has_kw = kw_lower in context.section_text.lower()
            opt_has_kw = kw_lower in optimized.lower()
            if orig_has_kw and not opt_has_kw:
                warnings.append(f"Primary keyword '{context.primary_keyword}' lost during optimization")

        # Verify no content loss
        if len(optimized) < len(context.section_text) * 0.3:
            warnings.append("Optimized content is significantly shorter than original")
            return context.section_text, warnings

        return optimized, warnings

    def quick_seo_fixes(self, text: str, primary_keyword: str) -> tuple[str, list[str]]:
        fixes: list[str] = []
        modified = text

        if not primary_keyword:
            return text, fixes

        kw = primary_keyword.lower()
        text_lower = modified.lower()

        # Fix 1: Ensure keyword is in first paragraph
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', modified) if p.strip()]
        if paragraphs and kw not in paragraphs[0].lower():
            first_sentence = paragraphs[0].split('.')[0]
            if kw not in first_sentence.lower():
                import random
                connectors = ["In particular,", "Specifically,", "Notably,", "In this context,"]
                connector = random.choice(connectors)
                insertion = f" {connector} {primary_keyword.title()} is a key concept. "
                modified = modified.replace(first_sentence + ".", first_sentence + "." + insertion, 1)
                fixes.append("Added primary keyword to first paragraph")

        # Fix 2: Ensure keyword is in last paragraph
        if paragraphs and kw not in paragraphs[-1].lower():
            if len(paragraphs) > 1:
                fixes.append("Primary keyword not in conclusion paragraph")

        # Fix 3: Add bold for keyword
        if kw in modified.lower() and f"**{primary_keyword}**" not in modified and f"**{primary_keyword.lower()}**" not in modified.lower():
            pattern = re.compile(re.escape(primary_keyword), re.IGNORECASE)
            match = pattern.search(modified)
            if match:
                start = match.start()
                end = match.end()
                modified = modified[:start] + "**" + modified[start:end] + "**" + modified[end:]
                fixes.append("Bolded first occurrence of primary keyword")

        return modified, fixes
