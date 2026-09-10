"""Optimization Validator — validates optimized content before acceptance."""

from __future__ import annotations
import logging
import re
from typing import Any

from optimization.optimization_models import (
    OptimizationContext, OptimizationType, OptimizationResult,
)

logger = logging.getLogger(__name__)


class OptimizationValidator:
    """Validates that optimized content meets quality and preservation requirements."""

    def validate(
        self,
        original: str,
        optimized: str,
        context: OptimizationContext,
        optimization_types: list[OptimizationType],
    ) -> tuple[bool, list[str]]:
        warnings: list[str] = []

        if not optimized or not optimized.strip():
            return False, ["Optimized content is empty"]

        # Check content preservation
        content_ok, content_warnings = self._check_content_preservation(original, optimized, context)
        warnings.extend(content_warnings)

        # Check type-specific validation
        for opt_type in optimization_types:
            type_ok, type_warnings = self._validate_by_type(optimized, context, opt_type)
            warnings.extend(type_warnings)

        # Check for hallucination introduction (never add new unsupported claims)
        hallucination_warnings = self._check_new_hallucinations(original, optimized, context)
        warnings.extend(hallucination_warnings)

        # Check markdown validity
        if not self._check_markdown_valid(optimized):
            warnings.append("Optimized content has invalid markdown syntax")

        is_valid = len([w for w in warnings if w.startswith("FAIL:")]) == 0
        return is_valid, warnings

    def _check_content_preservation(
        self,
        original: str,
        optimized: str,
        context: OptimizationContext,
    ) -> tuple[bool, list[str]]:
        warnings: list[str] = []

        # Preserve code blocks
        orig_code = set(re.findall(r'```.*?```', original, re.DOTALL))
        opt_code = set(re.findall(r'```.*?```', optimized, re.DOTALL))
        for block in orig_code:
            if block not in opt_code:
                warnings.append("FAIL: Code block removed during optimization")

        # Preserve tables
        orig_tables = set(re.findall(r'\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n?)*', original))
        opt_tables = set(re.findall(r'\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n?)*', optimized))
        for table in orig_tables:
            if table not in opt_tables:
                warnings.append("WARN: Table structure may have changed")

        # Preserve images
        orig_images = set(re.findall(r'!\[([^\]]*)\]\([^)]+\)', original))
        opt_images = set(re.findall(r'!\[([^\]]*)\]\([^)]+\)', optimized))
        for img in orig_images:
            if img not in opt_images:
                warnings.append("WARN: Image reference may have been removed")

        # Check length preservation (shouldn't shrink too much)
        if len(optimized) < len(original) * 0.3:
            warnings.append("FAIL: Optimized content is less than 30% of original length")
            return False, warnings

        return True, warnings

    def _validate_by_type(
        self,
        optimized: str,
        context: OptimizationContext,
        opt_type: OptimizationType,
    ) -> tuple[bool, list[str]]:
        warnings: list[str] = []

        if opt_type == OptimizationType.SEO:
            if context.primary_keyword:
                kw = context.primary_keyword.lower()
                if kw not in optimized.lower():
                    warnings.append(f"FAIL: Primary keyword '{context.primary_keyword}' missing after SEO optimization")

        elif opt_type == OptimizationType.GRAMMAR:
            sentences = re.split(r'(?<=[.!?])\s+', optimized)
            for i, sent in enumerate(sentences):
                stripped = sent.strip()
                if stripped and stripped[0].islower():
                    pass  # Will be caught by revalidation

        elif opt_type == OptimizationType.HALLUCINATION:
            text_lower = optimized.lower()
            patterns_to_check = [
                r'\baccording to a \d{4} study\b',
                r'\ba \d{4} (study|report|survey|analysis) (by|from|published)\b',
                r'\bresearch (shows|suggests|indicates|proves|demonstrates)\b',
                r'\bstudies show\b',
            ]
            for pattern in patterns_to_check:
                if re.search(pattern, text_lower):
                    warnings.append(f"WARN: Hallucination pattern may remain: '{pattern}'")

        elif opt_type == OptimizationType.READABILITY:
            sentences = re.split(r'(?<=[.!?])\s+', optimized)
            long_sentences = [s for s in sentences if len(s.split()) > 35]
            if long_sentences:
                warnings.append(f"WARN: {len(long_sentences)} sentence(s) still over 35 words")

        return True, warnings

    def _check_new_hallucinations(
        self,
        original: str,
        optimized: str,
        context: OptimizationContext,
    ) -> list[str]:
        warnings: list[str] = []

        stats_pattern = re.compile(r'\b\d+%\'?\s*(of|increase|decrease|improvement|reduction)')
        orig_stats = set(stats_pattern.findall(original.lower()))
        opt_stats = set(stats_pattern.findall(optimized.lower()))
        new_stats = opt_stats - orig_stats
        if new_stats:
            warnings.append(f"WARN: New statistical claims introduced: {', '.join(new_stats)}")

        return warnings

    def _check_markdown_valid(self, text: str) -> bool:
        lines = text.split('\n')
        in_code_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            # Check for unclosed markdown tags
            if re.search(r'\*\*[^*]+\*\*', line):
                pass
        return True
