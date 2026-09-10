"""Problem & Importance Planner — identifies problems, impact, and urgency.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import ProblemAnalysis

logger = logging.getLogger(__name__)


class ProblemImportancePlanner:
    """Analyzes problems, pain points, and importance from knowledge graph and SEO plan."""

    def analyze(
        self,
        primary_keyword: str,
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> ProblemAnalysis:
        pa = ProblemAnalysis()
        kg = knowledge_graph or {}
        sp = seo_plan or {}
        analysis_data = analysis or {}

        pa.primary_problem = f"Lack of comprehensive understanding of {primary_keyword}"

        # Pain points from KG
        if isinstance(kg, dict):
            pain_points = kg.get("pain_points", [])
            if isinstance(pain_points, list):
                for pp in pain_points[:5]:
                    if isinstance(pp, dict):
                        problem = pp.get("problem", "")
                        if problem:
                            pa.secondary_problems.append(problem)
                            pa.reader_pain_points.append(problem)

        # Pain points from SEO plan
        if isinstance(sp, dict):
            ta = sp.get("target_audience", {})
            if isinstance(ta, dict):
                spp = ta.get("pain_points", [])
                if isinstance(spp, list):
                    for p in spp:
                        if isinstance(p, str) and p not in pa.reader_pain_points:
                            pa.reader_pain_points.append(p)

        # Pain points from analysis
        if isinstance(analysis_data, dict):
            app = analysis_data.get("pain_points", [])
            if isinstance(app, list):
                for p in app:
                    p_str = str(p) if not isinstance(p, str) else p
                    if p_str not in pa.reader_pain_points:
                        pa.reader_pain_points.append(p_str)

        if not pa.reader_pain_points:
            pa.reader_pain_points = [f"Understanding {primary_keyword} from scratch",
                                     f"Keeping up with latest {primary_keyword} developments"]

        pa.business_impact = (f"Organizations that master {primary_keyword} gain a significant "
                              f"competitive advantage in their industry")
        pa.importance = f"{primary_keyword} is becoming increasingly critical in today's technology landscape"
        pa.urgency = f"The demand for {primary_keyword} expertise is growing rapidly"
        pa.opportunity = f"Early adopters of {primary_keyword} best practices can establish market leadership"

        return pa
