"""Audience Engine — identifies target audience from analysis and knowledge graph.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import TargetAudience

logger = logging.getLogger(__name__)

AUDIENCE_MAP: dict[str, dict] = {
    "programming": {
        "audience": "Software Developers",
        "skill": "intermediate",
        "industry": ["Technology", "Software"],
        "roles": ["Software Engineer", "Developer", "Programmer"],
    },
    "data_science": {
        "audience": "Data Scientists",
        "skill": "intermediate",
        "industry": ["Technology", "Finance", "Healthcare"],
        "roles": ["Data Scientist", "Data Analyst", "ML Engineer"],
    },
    "ai": {
        "audience": "AI Practitioners",
        "skill": "advanced",
        "industry": ["Technology", "Research"],
        "roles": ["AI Engineer", "ML Engineer", "Researcher"],
    },
    "business": {
        "audience": "Business Professionals",
        "skill": "beginner",
        "industry": ["Business", "Consulting"],
        "roles": ["Manager", "Executive", "Analyst"],
    },
    "marketing": {
        "audience": "Marketers",
        "skill": "intermediate",
        "industry": ["Marketing", "Advertising"],
        "roles": ["SEO Specialist", "Content Marketer", "Digital Marketer"],
    },
    "design": {
        "audience": "Designers",
        "skill": "intermediate",
        "industry": ["Design", "Technology"],
        "roles": ["UI Designer", "UX Designer", "Product Designer"],
    },
    "devops": {
        "audience": "DevOps Engineers",
        "skill": "advanced",
        "industry": ["Technology", "Cloud"],
        "roles": ["DevOps Engineer", "SRE", "Platform Engineer"],
    },
    "analytics": {
        "audience": "Analytics Professionals",
        "skill": "intermediate",
        "industry": ["Technology", "Finance", "Marketing"],
        "roles": ["Data Analyst", "Business Analyst", "Analytics Engineer"],
    },
}


class AudienceEngine:
    """Identifies target audience from analysis content."""

    def identify(
        self,
        analysis: dict[str, Any] | None,
        knowledge_graph: dict[str, Any] | None,
    ) -> TargetAudience:
        audience = TargetAudience()
        analysis_data = analysis or {}

        if not isinstance(analysis_data, dict):
            return audience

        raw_audience = analysis_data.get("target_audience", "")
        if isinstance(raw_audience, str) and raw_audience:
            audience.primary_audience = raw_audience

        raw_level = analysis_data.get("experience_level", "")
        if isinstance(raw_level, str) and raw_level:
            audience.skill_level = raw_level.lower()

        raw_industry = analysis_data.get("industry", "")
        if isinstance(raw_industry, str) and raw_industry:
            audience.industry = [raw_industry]

        category = analysis_data.get("content_category", "")
        if isinstance(category, str) and category:
            mapping = AUDIENCE_MAP.get(category.lower())
            if mapping:
                if not audience.primary_audience:
                    audience.primary_audience = mapping["audience"]
                if not audience.skill_level:
                    audience.skill_level = mapping["skill"]
                if not audience.industry:
                    audience.industry = list(mapping["industry"])
                if not audience.job_roles:
                    audience.job_roles = list(mapping["roles"])

        # Extract pain points from KG
        if isinstance(knowledge_graph, dict):
            pain_points = knowledge_graph.get("pain_points", [])
            if isinstance(pain_points, list):
                for pp in pain_points[:5]:
                    if isinstance(pp, dict):
                        problem = pp.get("problem", "")
                        if problem:
                            audience.pain_points.append(problem)

        if not audience.primary_audience:
            audience.primary_audience = "General Audience"
            audience.skill_level = "beginner"

        return audience
