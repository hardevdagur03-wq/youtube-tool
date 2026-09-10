"""Retry Manager — maximum 3 retries with quality gate checks between attempts."""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

from optimization.optimization_models import (
    OptimizationType, OptimizationStatus, QualityGate, OptimizationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class RetryState:
    section_index: int = 0
    optimization_types: list[OptimizationType] = field(default_factory=list)
    attempts: int = 0
    max_retries: int = 3
    history: list[dict] = field(default_factory=list)
    scores_history: list[dict[str, float]] = field(default_factory=list)
    exhausted: bool = False


class RetryManager:
    """Manages retry logic with quality gate checks and exponential awareness."""

    def __init__(self, max_retries: int = 3, quality_gates: QualityGate | None = None):
        self._max_retries = max_retries
        self._quality_gates = quality_gates or QualityGate()
        self._states: dict[int, RetryState] = {}

    def can_retry(self, section_index: int) -> bool:
        state = self._states.get(section_index)
        if not state:
            return True
        return state.attempts < state.max_retries and not state.exhausted

    def record_attempt(
        self,
        section_index: int,
        optimization_types: list[OptimizationType],
        scores_after: dict[str, float],
    ) -> bool:
        state = self._states.setdefault(
            section_index,
            RetryState(
                section_index=section_index,
                optimization_types=optimization_types,
                max_retries=self._max_retries,
            ),
        )
        state.attempts += 1
        state.scores_history.append(dict(scores_after))

        passed = self._check_quality_gates(scores_after, optimization_types)
        if passed:
            logger.info(
                "[RetryManager] Section %d passed quality gates on attempt %d/%d",
                section_index, state.attempts, state.max_retries,
            )
            return True

        if state.attempts >= state.max_retries:
            state.exhausted = True
            logger.warning(
                "[RetryManager] Section %d exhausted after %d attempts",
                section_index, state.attempts,
            )
            return False

        logger.info(
            "[RetryManager] Section %d attempt %d/%d did not pass gates, retrying",
            section_index, state.attempts, state.max_retries,
        )
        return False

    def get_attempt_count(self, section_index: int) -> int:
        state = self._states.get(section_index)
        return state.attempts if state else 0

    def get_improvement_trend(self, section_index: int) -> str:
        state = self._states.get(section_index)
        if not state or len(state.scores_history) < 2:
            return "stable"
        latest = state.scores_history[-1]
        previous = state.scores_history[-2]
        for key in latest:
            if latest.get(key, 0) > previous.get(key, 0) + 2:
                return "improving"
            if latest.get(key, 0) < previous.get(key, 0) - 2:
                return "degrading"
        return "stable"

    def mark_section_result(self, section_index: int, result: OptimizationResult) -> None:
        state = self._states.get(section_index)
        if state and state.exhausted and result.status != OptimizationStatus.ROLLED_BACK:
            result.status = OptimizationStatus.MAX_RETRIES_EXCEEDED
            result.warnings.append("Max retries exceeded without passing quality gates")

    def _check_quality_gates(self, scores: dict[str, float], optimization_types: list[OptimizationType]) -> bool:
        if not scores:
            return False

        for opt_type in optimization_types:
            key = self._score_key(opt_type)
            threshold = self._threshold_for_type(opt_type)
            current = scores.get(key, 0)
            if current < threshold:
                logger.debug("[RetryManager] Gate failed: %s = %.1f < %.1f", key, current, threshold)
                return False

        return True

    def _score_key(self, opt_type: OptimizationType) -> str:
        mapping = {
            OptimizationType.SEO: "seo",
            OptimizationType.GRAMMAR: "grammar",
            OptimizationType.READABILITY: "readability",
            OptimizationType.HALLUCINATION: "hallucination_risk",
            OptimizationType.KEYWORD: "keyword_optimization",
            OptimizationType.PASSIVE_VOICE: "grammar",
            OptimizationType.MARKDOWN: "markdown_quality",
            OptimizationType.DUPLICATE: "structure",
            OptimizationType.STRUCTURE: "structure",
            OptimizationType.STYLE: "content_quality",
            OptimizationType.COMPLETENESS: "completeness",
            OptimizationType.FAQ: "completeness",
            OptimizationType.CTA: "completeness",
            OptimizationType.SUMMARY: "completeness",
        }
        return mapping.get(opt_type, "overall")

    def _threshold_for_type(self, opt_type: OptimizationType) -> float:
        gates = self._quality_gates
        mapping = {
            OptimizationType.SEO: gates.seo_min,
            OptimizationType.GRAMMAR: gates.grammar_min,
            OptimizationType.READABILITY: gates.readability_min,
            OptimizationType.HALLUCINATION: 90.0,
            OptimizationType.KEYWORD: 85.0,
            OptimizationType.PASSIVE_VOICE: gates.grammar_min,
            OptimizationType.MARKDOWN: 95.0,
            OptimizationType.DUPLICATE: 85.0,
            OptimizationType.STRUCTURE: 85.0,
            OptimizationType.STYLE: 85.0,
            OptimizationType.COMPLETENESS: 85.0,
            OptimizationType.FAQ: 85.0,
            OptimizationType.CTA: 85.0,
            OptimizationType.SUMMARY: 85.0,
        }
        return mapping.get(opt_type, 85.0)

    def clear(self) -> None:
        self._states.clear()
