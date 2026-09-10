"""Optimization Planner — analyzes review report and plans which sections need what optimization."""

from __future__ import annotations
import logging
import re
from typing import Any

from optimization.optimization_models import (
    OptimizationType, SectionType, OptimizationPlan, QualityGate,
)

logger = logging.getLogger(__name__)

SECTION_TYPE_KEYWORDS = {
    SectionType.INTRODUCTION: ["introduction", "intro", "overview", "background", "getting started"],
    SectionType.CONCLUSION: ["conclusion", "summary", "wrap-up", "final thoughts", "key takeaways"],
    SectionType.CTA: ["call to action", "cta", "next steps", "get started", "sign up"],
    SectionType.FAQ: ["faq", "frequently asked questions", "common questions"],
    SectionType.SUMMARY: ["summary", "key points", "recap", "in summary", "to summarize"],
    SectionType.TABLE: ["table", "comparison", "chart", "matrix"],
    SectionType.LIST: ["list", "checklist", "steps", "items", "bullets"],
    SectionType.EXAMPLE: ["example", "sample", "instance", "case study", "illustration"],
    SectionType.CODE_BLOCK: ["code", "syntax", "command", "script", "function"],
    SectionType.QUOTE: ["quote", "testimonial", "citation", "reference"],
}


class OptimizationPlanner:
    """Analyzes review report and plans targeted optimization for each section."""

    def __init__(self, quality_gates: QualityGate | None = None):
        self._quality_gates = quality_gates or QualityGate()

    def plan(
        self,
        sections: list[dict],
        review_scores: dict[str, float],
        review_issues: list[dict],
        recommendations: list[dict],
        primary_keyword: str,
    ) -> list[OptimizationPlan]:
        plans: list[OptimizationPlan] = []

        for i, section in enumerate(sections):
            heading = section.get("heading", f"Section {i+1}")
            text = section.get("content", "")
            section_type = self._detect_section_type(heading, text)
            quality_scores = self._get_section_scores(heading, text, review_scores)
            issues = self._filter_issues_for_section(heading, text, review_issues)

            plan = self._create_plan(
                section_index=i,
                heading=heading,
                section_type=section_type,
                quality_scores=quality_scores,
                issues=issues,
                recommendations=recommendations,
                primary_keyword=primary_keyword,
            )
            plans.append(plan)

        plans.sort(key=lambda p: p.priority, reverse=True)
        return plans

    def _detect_section_type(self, heading: str, text: str) -> SectionType:
        heading_lower = heading.lower().strip()

        # Check for table markers
        if '|' in text and re.search(r'\|.+\|\n\|[-:| ]+\|', text):
            return SectionType.TABLE

        # Check for code blocks
        if re.search(r'```\w*', text):
            return SectionType.CODE_BLOCK

        # Check for list patterns
        if re.search(r'^[-*+]\s', text, re.MULTILINE) or re.search(r'^\d+[.)]\s', text, re.MULTILINE):
            if not re.search(r'^##|^#', text, re.MULTILINE):
                return SectionType.LIST

        # Match heading keywords
        for s_type, keywords in SECTION_TYPE_KEYWORDS.items():
            if any(kw in heading_lower for kw in keywords):
                return s_type

        paragraphs = re.split(r'\n\s*\n', text.strip())
        if len(paragraphs) <= 2 and len(text.split()) < 50:
            return SectionType.QUOTE

        return SectionType.BODY

    def _get_section_scores(
        self,
        heading: str,
        text: str,
        review_scores: dict[str, float],
    ) -> dict[str, float]:
        return dict(review_scores) if isinstance(review_scores, dict) else {}

    def _filter_issues_for_section(
        self,
        heading: str,
        text: str,
        issues: list[dict],
    ) -> list[dict]:
        if not issues:
            return []
        heading_lower = heading.lower()
        text_lower = text.lower()[:500]
        relevant = []
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            desc = issue.get("description", "").lower()
            loc = issue.get("location", "").lower()
            if heading_lower and (heading_lower in loc or heading_lower in desc):
                relevant.append(issue)
            elif text_lower and any(word in text_lower for word in desc.split()[:5]):
                relevant.append(issue)
        return relevant[:10]

    def _create_plan(
        self,
        section_index: int,
        heading: str,
        section_type: SectionType,
        quality_scores: dict[str, float],
        issues: list[dict],
        recommendations: list[dict],
        primary_keyword: str,
    ) -> OptimizationPlan:
        optimization_types: list[OptimizationType] = []
        reasons: list[str] = []
        priority = 0

        seo_score = quality_scores.get("seo", 100.0)
        grammar_score = quality_scores.get("grammar", 100.0)
        readability_score = quality_scores.get("readability", 100.0)
        hallucination_score = quality_scores.get("hallucination_risk", 100.0)
        keyword_score = quality_scores.get("keyword_optimization", 100.0)
        markdown_score = quality_scores.get("markdown_quality", 100.0)
        structure_score = quality_scores.get("structure", 100.0)
        content_quality_score = quality_scores.get("content_quality", 100.0)
        completeness_score = quality_scores.get("completeness", 100.0)

        # Check each quality gate
        if seo_score < self._quality_gates.seo_min:
            optimization_types.append(OptimizationType.SEO)
            reasons.append(f"SEO score {seo_score:.0f} < {self._quality_gates.seo_min:.0f}")
            priority += 10

        if grammar_score < self._quality_gates.grammar_min:
            optimization_types.append(OptimizationType.GRAMMAR)
            reasons.append(f"Grammar score {grammar_score:.0f} < {self._quality_gates.grammar_min:.0f}")
            priority += 8

        if readability_score < self._quality_gates.readability_min:
            optimization_types.append(OptimizationType.READABILITY)
            reasons.append(f"Readability score {readability_score:.0f} < {self._quality_gates.readability_min:.0f}")
            priority += 7

        if hallucination_score < 90.0:
            optimization_types.append(OptimizationType.HALLUCINATION)
            reasons.append(f"Hallucination risk score {hallucination_score:.0f} < 90")
            priority += 9

        if keyword_score < 85.0 and primary_keyword:
            optimization_types.append(OptimizationType.KEYWORD)
            reasons.append(f"Keyword score {keyword_score:.0f} < 85")
            priority += 6

        if markdown_score < 95.0:
            optimization_types.append(OptimizationType.MARKDOWN)
            reasons.append(f"Markdown score {markdown_score:.0f} < 95")
            priority += 4

        if structure_score < 85.0:
            optimization_types.append(OptimizationType.STRUCTURE)
            reasons.append(f"Structure score {structure_score:.0f} < 85")
            priority += 5

        if content_quality_score < 85.0:
            optimization_types.append(OptimizationType.STYLE)
            reasons.append(f"Content quality score {content_quality_score:.0f} < 85")
            priority += 3

        if section_type in (SectionType.SUMMARY, SectionType.FAQ, SectionType.CTA) and completeness_score < 85.0:
            opt_type_map = {
                SectionType.SUMMARY: OptimizationType.SUMMARY,
                SectionType.FAQ: OptimizationType.FAQ,
                SectionType.CTA: OptimizationType.CTA,
            }
            optimization_types.append(opt_type_map.get(section_type, OptimizationType.COMPLETENESS))
            reasons.append(f"{section_type.value} completeness {completeness_score:.0f} < 85")
            priority += 6

        # Check for specific issues
        for issue in issues:
            desc = issue.get("description", "") if isinstance(issue, dict) else str(issue)
            desc_lower = desc.lower()

            if "passive voice" in desc_lower and OptimizationType.PASSIVE_VOICE not in optimization_types:
                optimization_types.append(OptimizationType.PASSIVE_VOICE)
                reasons.append("Passive voice detected")
                priority += 5

            if "duplicate" in desc_lower and OptimizationType.DUPLICATE not in optimization_types:
                optimization_types.append(OptimizationType.DUPLICATE)
                reasons.append("Duplicate content detected")
                priority += 4

        return OptimizationPlan(
            section_index=section_index,
            section_heading=heading,
            section_type=section_type,
            optimization_types=optimization_types,
            priority=priority,
            quality_scores=quality_scores,
            issues=issues,
            needs_optimization=len(optimization_types) > 0,
            reason="; ".join(reasons) if reasons else "All quality gates passed",
        )
