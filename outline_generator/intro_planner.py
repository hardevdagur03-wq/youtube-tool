"""Intro Planner — plans the introduction structure.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import IntroPlan

logger = logging.getLogger(__name__)


class IntroPlanner:
    """Plans the introduction: hook, problem, context, promise, transition."""

    def plan(
        self,
        primary_keyword: str,
        target_audience: str = "",
        analysis: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
    ) -> IntroPlan:
        plan = IntroPlan()
        analysis_data = analysis or {}
        sp = seo_plan or {}

        audience = target_audience or "readers"
        pain_points: list[str] = []

        if isinstance(sp, dict):
            ta = sp.get("target_audience", {})
            if isinstance(ta, dict):
                pain_points = ta.get("pain_points", [])
                if isinstance(pain_points, str):
                    pain_points = [pain_points]

        if not pain_points and isinstance(analysis_data, dict):
            pp = analysis_data.get("pain_points", [])
            if isinstance(pp, list):
                pain_points = [str(p) for p in pp if isinstance(p, str)]

        primary_problem = pain_points[0] if pain_points else f"understanding and implementing {primary_keyword}"

        plan.hook_approach = f"Start with a compelling stat or question about {primary_keyword}"
        plan.problem_intro = primary_problem[:200]
        plan.context = f"Setting the context for why {primary_keyword} matters in today's landscape"
        plan.importance_statement = (f"Understanding {primary_keyword} is crucial for {audience} "
                                     f"looking to stay competitive and achieve better results")
        plan.reader_promise = (f"By the end of this guide, you will have a comprehensive understanding "
                               f"of {primary_keyword} and actionable steps to implement it")
        plan.reader_expectation = "This guide covers fundamentals, advanced techniques, best practices, and real-world examples"
        plan.transition = f"Let's dive deep into {primary_keyword} and explore everything you need to know"

        plan.target_word_count = 150

        return plan
