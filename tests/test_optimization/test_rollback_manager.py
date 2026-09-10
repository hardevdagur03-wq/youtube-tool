"""Tests for RollbackManager."""

from __future__ import annotations
from optimization.rollback_manager import RollbackManager
from optimization.optimization_models import (
    OptimizationType, OptimizationResult, OptimizationStatus, SectionType, SectionVersion,
)


class TestRollbackManager:
    def test_init(self):
        rm = RollbackManager()
        assert rm is not None

    def test_should_rollback_degradation(self):
        rm = RollbackManager()
        should, reason = rm.should_rollback(
            {"seo": 90.0, "grammar": 95.0},
            {"seo": 70.0, "grammar": 95.0},
            [OptimizationType.SEO],
        )
        assert should is True
        assert "seo" in reason.lower()

    def test_should_not_rollback_improvement(self):
        rm = RollbackManager()
        should, reason = rm.should_rollback(
            {"seo": 70.0, "grammar": 80.0},
            {"seo": 95.0, "grammar": 85.0},
            [OptimizationType.SEO],
        )
        assert should is False
        assert reason == ""

    def test_should_not_rollback_equal(self):
        rm = RollbackManager()
        should, reason = rm.should_rollback(
            {"seo": 85.0},
            {"seo": 85.0},
            [OptimizationType.SEO],
        )
        assert should is False

    def test_should_rollback_below_threshold(self):
        rm = RollbackManager()
        should, reason = rm.should_rollback(
            {"seo": 95.0},
            {"seo": 80.0},
            [OptimizationType.SEO],
            thresholds={"seo": 90.0},
        )
        assert should is True
        assert "threshold" in reason.lower()

    def test_execute_rollback(self):
        rm = RollbackManager()
        result = OptimizationResult(
            section_index=0,
            section_heading="Intro",
            content_before="Original",
            content_after="Bad optimization",
            scores_before={"seo": 90.0},
            scores_after={"seo": 50.0},
        )
        version = SectionVersion(
            version_id="v1",
            section_index=0,
            section_heading="Intro",
            content_before="Original",
            content_after="Original",
            scores_before={"seo": 90.0},
            scores_after={"seo": 90.0},
            optimization_type=OptimizationType.SEO,
        )
        result = rm.execute_rollback(result, version, "SEO score dropped")
        assert result.rolled_back is True
        assert result.content_after == "Original"
        assert result.status == OptimizationStatus.ROLLED_BACK

    def test_execute_rollback_no_version(self):
        rm = RollbackManager()
        result = OptimizationResult(section_index=0, section_heading="Intro")
        result = rm.execute_rollback(result, None, "No version")
        assert result.rolled_back is False
        assert len(result.warnings) > 0

    def test_get_rollback_events(self):
        rm = RollbackManager()
        assert rm.get_rollback_events() == []

    def test_clear(self):
        rm = RollbackManager()
        rm._rollback_events.append({"test": True})
        rm.clear()
        assert rm.get_rollback_events() == []

    def test_score_key_for_type(self):
        assert RollbackManager._score_key_for_type(OptimizationType.SEO) == "seo"
        assert RollbackManager._score_key_for_type(OptimizationType.GRAMMAR) == "grammar"
        assert RollbackManager._score_key_for_type(OptimizationType.HALLUCINATION) == "hallucination_risk"
