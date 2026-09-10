"""Context Manager — loads only relevant context for a given section optimization."""

from __future__ import annotations
import json
import logging
import os
from typing import Any

from optimization.optimization_models import (
    OptimizationContext, OptimizationType, SectionType,
)

logger = logging.getLogger(__name__)


class OptimizationContextManager:
    """Loads minimal relevant context for section optimization."""

    def __init__(self, project_dir: str | None = None):
        self._project_dir = project_dir
        self._artifacts: dict[str, Any] = {}

    def load_artifacts(self, project_dir: str | None = None) -> dict[str, Any]:
        directory = project_dir or self._project_dir
        if not directory:
            return {}

        cache_key = f"artifacts_{directory}"
        if cache_key in self._artifacts:
            return self._artifacts[cache_key]

        artifacts: dict[str, Any] = {}
        paths = {
            "outline": "outline.json",
            "seo_plan": "seo_plan.json",
            "knowledge_graph": "knowledge_graph.json",
            "project": "project.json",
            "review_report": "review_report.json",
        }

        for key, filename in paths.items():
            path = os.path.join(directory, filename)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        artifacts[key] = json.load(f)
                except Exception as exc:
                    logger.warning("[ContextManager] Failed loading %s: %s", path, exc)
                    artifacts[key] = {}

        self._artifacts[cache_key] = artifacts
        logger.debug("[ContextManager] Loaded %d artifacts from %s", len(artifacts), directory)
        return artifacts

    def build_context(
        self,
        section_index: int,
        section_text: str,
        section_heading: str,
        section_type: SectionType,
        optimization_types: list[OptimizationType],
        artifacts: dict[str, Any],
        project_id: str = "",
        blog_title: str = "",
    ) -> OptimizationContext:
        outline = artifacts.get("outline", {})
        seo_plan = artifacts.get("seo_plan", {})
        kg = artifacts.get("knowledge_graph", {})
        review = artifacts.get("review_report", {})

        scores = review.get("quality_scores", {}) if isinstance(review, dict) else {}
        issues = review.get("issues", []) if isinstance(review, dict) else []
        recommendations = review.get("recommendations", []) if isinstance(review, dict) else []

        relevant_issues = self._filter_relevant_issues(section_heading, section_text, issues)
        relevant_recs = self._filter_relevant_recommendations(section_heading, recommendations)

        # Extract keyword info
        kw_strategy = seo_plan.get("keyword_strategy", {}) if isinstance(seo_plan, dict) else {}
        primary_kw = ""
        secondary_kws: list[str] = []
        if isinstance(kw_strategy, dict):
            primary_kw = kw_strategy.get("primary", "") or seo_plan.get("primary_keyword", "")
            secondary_kws = kw_strategy.get("secondary", []) or seo_plan.get("secondary_keywords", [])

        # Build outline section context
        outline_section = self._find_outline_section(section_heading, outline)

        return OptimizationContext(
            section_text=section_text,
            section_heading=section_heading,
            section_type=section_type,
            outline_section=outline_section,
            seo_plan=seo_plan,
            knowledge_graph=kg,
            review_findings=relevant_issues,
            quality_scores=scores if isinstance(scores, dict) else {},
            issues=relevant_issues,
            recommendations=relevant_recs,
            primary_keyword=primary_kw,
            secondary_keywords=secondary_kws,
            blog_title=blog_title,
            project_id=project_id,
        )

    def _filter_relevant_issues(self, heading: str, text: str, issues: list) -> list[dict]:
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
            elif text_lower and desc and any(word in text_lower for word in desc.split()[:5]):
                relevant.append(issue)
        return relevant[:10]

    def _filter_relevant_recommendations(self, heading: str, recommendations: list) -> list[dict]:
        if not recommendations:
            return []
        heading_lower = heading.lower()
        relevant = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            desc = rec.get("description", "").lower()
            if heading_lower and heading_lower in desc:
                relevant.append(rec)
        return relevant[:5]

    def _find_outline_section(self, heading: str, outline: Any) -> dict:
        if not isinstance(outline, dict):
            return {}
        sections = outline.get("sections", []) if isinstance(outline, dict) else []
        if not sections:
            return {}
        heading_lower = heading.lower().strip().lstrip("#").strip()
        for sec in sections:
            sec_heading = sec.get("heading", "") if isinstance(sec, dict) else ""
            if sec_heading.lower().strip() == heading_lower:
                return sec
            if isinstance(sec, dict) and heading_lower in sec_heading.lower():
                return sec
        return {}

    def clear_cache(self) -> None:
        self._artifacts.clear()
