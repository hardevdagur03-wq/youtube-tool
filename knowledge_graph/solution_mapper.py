"""Solution Mapper — maps solutions to identified problems.

Consumes analysis.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from knowledge_graph.knowledge_graph_models import Solution, Confidence

logger = logging.getLogger(__name__)


class SolutionMapper:
    """Maps solutions to problems from analysis and transcript."""

    def map(
        self,
        analysis: dict[str, Any] | None,
        pain_point_problems: list[str],
    ) -> list[Solution]:
        solutions: list[Solution] = []
        seen_problem: set[str] = set()

        if not analysis or not isinstance(analysis, dict):
            return solutions

        for field in ("solutions", "recommendations", "action_items", "main_solution", "opportunities"):
            items = analysis.get(field, [])
            if isinstance(items, str) and items.strip():
                items = [items]
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str) and item.strip():
                        problem = self._find_best_problem(item, pain_point_problems)
                        if problem and problem.lower() not in seen_problem:
                            seen_problem.add(problem.lower())
                            solutions.append(Solution(
                                problem=problem,
                                solution=item[:500],
                                confidence=Confidence.MEDIUM,
                                benefits=[],
                                limitations=[],
                            ))

        return solutions

    def _find_best_problem(self, solution_text: str, problems: list[str]) -> str:
        if not problems:
            return "general"
        solution_lower = solution_text.lower()
        for problem in problems:
            words = problem.lower().split()[:3]
            if any(word in solution_lower for word in words if len(word) > 3):
                return problem
        return problems[0] if problems else "general"
