"""Tests for RetryManager."""

from __future__ import annotations
from optimization.retry_manager import RetryManager
from optimization.optimization_models import QualityGate, OptimizationType, OptimizationResult, OptimizationStatus


class TestRetryManager:
    def test_init(self):
        rm = RetryManager()
        assert rm is not None
        assert rm._max_retries == 3

    def test_can_retry_new_section(self):
        rm = RetryManager()
        assert rm.can_retry(0) is True

    def test_record_attempt_passes_gates(self):
        rm = RetryManager(max_retries=3)
        passed = rm.record_attempt(
            0, [OptimizationType.SEO], {"seo": 95.0},
        )
        assert passed is True
        assert rm.get_attempt_count(0) == 1

    def test_record_attempt_fails_gates(self):
        rm = RetryManager(max_retries=3)
        passed = rm.record_attempt(
            0, [OptimizationType.SEO], {"seo": 50.0},
        )
        assert passed is False

    def test_record_attempt_exhausted(self):
        rm = RetryManager(max_retries=3)
        for _ in range(3):
            rm.record_attempt(0, [OptimizationType.SEO], {"seo": 50.0})
        assert rm.can_retry(0) is False
        state = rm._states.get(0)
        assert state.exhausted is True

    def test_get_attempt_count(self):
        rm = RetryManager()
        assert rm.get_attempt_count(99) == 0
        rm.record_attempt(1, [OptimizationType.SEO], {"seo": 80.0})
        assert rm.get_attempt_count(1) == 1

    def test_get_improvement_trend(self):
        rm = RetryManager()
        rm.record_attempt(0, [OptimizationType.SEO], {"seo": 70.0})
        rm.record_attempt(0, [OptimizationType.SEO], {"seo": 85.0})
        trend = rm.get_improvement_trend(0)
        assert trend in ("improving", "stable")

    def test_mark_section_result_exhausted(self):
        rm = RetryManager(max_retries=1)
        rm.record_attempt(0, [OptimizationType.SEO], {"seo": 50.0})
        result = OptimizationResult(
            section_index=0, section_heading="Test",
            status=OptimizationStatus.PENDING,
            scores_after={"seo": 50.0},
        )
        rm.mark_section_result(0, result)
        assert result.status == OptimizationStatus.MAX_RETRIES_EXCEEDED

    def test_clear(self):
        rm = RetryManager()
        rm.record_attempt(0, [OptimizationType.SEO], {"seo": 90.0})
        rm.clear()
        assert rm._states == {}

    def test_quality_gates_custom(self):
        gates = QualityGate(seo_min=80.0, grammar_min=85.0)
        rm = RetryManager(max_retries=3, quality_gates=gates)
        assert rm._quality_gates.seo_min == 80.0
