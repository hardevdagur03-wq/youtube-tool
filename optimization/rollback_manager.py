"""Rollback Manager — automatically rollback if optimization decreases quality."""

from __future__ import annotations
import logging
from typing import Any

from optimization.optimization_models import (
    SectionVersion, OptimizationResult, OptimizationStatus,
    OptimizationType,
)

logger = logging.getLogger(__name__)


class RollbackManager:
    """Detects quality degradation and performs automatic rollback."""

    def __init__(self):
        self._rollback_events: list[dict] = []

    def should_rollback(
        self,
        scores_before: dict[str, float],
        scores_after: dict[str, float],
        optimization_types: list[OptimizationType],
        thresholds: dict[str, float] | None = None,
    ) -> tuple[bool, str]:
        if not scores_before or not scores_after:
            return False, ""

        if thresholds is None:
            thresholds = {"seo": 90.0, "grammar": 95.0, "readability": 90.0}

        reasons: list[str] = []

        for opt_type in optimization_types:
            key = self._score_key_for_type(opt_type)
            before = scores_before.get(key, 0)
            after = scores_after.get(key, 0)
            threshold = thresholds.get(key, 70)

            if before > 0 and after < before - 5:
                reasons.append(f"{key} dropped from {before:.1f} to {after:.1f}")
            if after < threshold and before >= threshold:
                reasons.append(f"{key} fell below threshold ({threshold})")

        if reasons:
            return True, "; ".join(reasons)
        return False, ""

    def execute_rollback(
        self,
        result: OptimizationResult,
        version: SectionVersion | None,
        reason: str,
    ) -> OptimizationResult:
        if version is None:
            logger.warning("[RollbackManager] No version to rollback to for section %d", result.section_index)
            result.warnings.append("Rollback requested but no previous version available")
            return result

        result.content_after = version.content_before
        result.scores_after = dict(version.scores_before)
        result.rolled_back = True
        result.rollback_reason = reason
        result.status = OptimizationStatus.ROLLED_BACK

        self._rollback_events.append({
            "section_index": result.section_index,
            "section_heading": result.section_heading,
            "reason": reason,
            "rolled_back_to_version": version.version_id,
            "scores_before_rollback": dict(result.scores_before),
            "scores_after_rollback": dict(result.scores_after),
        })

        logger.info(
            "[RollbackManager] Rolled back section %d (%s): %s",
            result.section_index, result.section_heading, reason,
        )
        return result

    def get_rollback_events(self) -> list[dict]:
        return self._rollback_events

    def clear(self) -> None:
        self._rollback_events.clear()

    @staticmethod
    def _score_key_for_type(opt_type: OptimizationType) -> str:
        mapping = {
            OptimizationType.SEO: "seo",
            OptimizationType.GRAMMAR: "grammar",
            OptimizationType.READABILITY: "readability",
            OptimizationType.HALLUCINATION: "hallucination_risk",
            OptimizationType.KEYWORD: "keyword_optimization",
            OptimizationType.PASSIVE_VOICE: "grammar",
            OptimizationType.MARKDOWN: "markdown_quality",
            OptimizationType.STRUCTURE: "structure",
            OptimizationType.STYLE: "content_quality",
            OptimizationType.COMPLETENESS: "completeness",
            OptimizationType.FAQ: "completeness",
            OptimizationType.CTA: "completeness",
            OptimizationType.SUMMARY: "completeness",
            OptimizationType.DUPLICATE: "structure",
        }
        return mapping.get(opt_type, "overall")
