"""Tests for RetryManager — retry logic, backoff, jitter, non-recoverable errors."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from background_processing.models import JobModel
from background_processing.retry_manager import RetryManager, NON_RECOVERABLE_ERRORS


@pytest.fixture
def retry_mgr():
    return RetryManager()


def _make_job(attempts: int = 0, max_retries: int = 3) -> JobModel:
    import uuid
    from datetime import datetime, timezone
    return JobModel(
        uuid=str(uuid.uuid4()),
        job_type="pipeline.test",
        project_id="proj-1",
        status="failed",
        attempts=attempts,
        max_retries=max_retries,
        queue="default",
    )


class TestRetryManager:
    def test_should_retry_first_attempt(self, retry_mgr):
        job = _make_job(attempts=0)
        decision = retry_mgr.should_retry(job)
        assert decision.should_retry is True
        assert decision.send_to_dead_letter is False
        assert decision.delay > 0

    def test_should_retry_second_attempt(self, retry_mgr):
        job = _make_job(attempts=1)
        decision = retry_mgr.should_retry(job)
        assert decision.should_retry is True

    def test_should_not_retry_after_max(self, retry_mgr):
        job = _make_job(attempts=3)
        decision = retry_mgr.should_retry(job)
        assert decision.should_retry is False
        assert decision.send_to_dead_letter is True
        assert "Exceeded max retries" in decision.reason

    def test_non_recoverable_error(self, retry_mgr):
        for error in NON_RECOVERABLE_ERRORS:
            job = _make_job(attempts=0)
            decision = retry_mgr.should_retry(job, error=error)
            assert decision.should_retry is False, f"Should not retry: {error}"
            assert decision.send_to_dead_letter is True

    def test_recoverable_error(self, retry_mgr):
        job = _make_job(attempts=0)
        decision = retry_mgr.should_retry(job, error="TimeoutError: request timed out")
        assert decision.should_retry is True

    def test_exponential_backoff_increases(self, retry_mgr):
        with patch.object(retry_mgr._config, "default_retry_delay", 60):
            delay_1 = retry_mgr._compute_delay(1)
            delay_2 = retry_mgr._compute_delay(2)
            delay_3 = retry_mgr._compute_delay(3)
            assert delay_2 >= delay_1
            assert delay_3 >= delay_2

    def test_backoff_capped_at_max(self, retry_mgr):
        with patch.object(retry_mgr._config, "default_retry_delay", 60):
            with patch.object(retry_mgr._config, "default_retry_backoff_max", 300):
                delay = retry_mgr._compute_delay(10)
                assert delay <= 300

    def test_jitter_randomizes_delay(self, retry_mgr):
        with patch.object(retry_mgr._config, "retry_jitter", True):
            delays = {retry_mgr._compute_delay(2) for _ in range(50)}
            assert len(delays) > 1

    def test_linear_retry_when_backoff_disabled(self, retry_mgr):
        with patch.object(retry_mgr._config, "default_retry_backoff", False):
            with patch.object(retry_mgr._config, "retry_jitter", False):
                with patch.object(retry_mgr._config, "default_retry_delay", 30):
                    d1 = retry_mgr._compute_delay(1)
                    d2 = retry_mgr._compute_delay(5)
                    assert d1 == d2 == 30

    def test_estimate_retry_delay(self, retry_mgr):
        job = _make_job(attempts=0)
        delay = retry_mgr.estimate_retry_delay(job)
        assert delay > 0

    def test_build_retry_history(self, retry_mgr):
        job = _make_job(attempts=0)
        history = retry_mgr.build_retry_history(job, error="test error", traceback="trace")
        assert len(history) == 1
        assert history[0]["attempt"] == 1
        assert history[0]["error"] == "test error"
        assert history[0]["traceback"] == "trace"

    def test_build_retry_history_appends(self, retry_mgr):
        job = _make_job(attempts=1)
        job.retry_history = [{"attempt": 1, "error": "prev"}]
        history = retry_mgr.build_retry_history(job, error="new error")
        assert len(history) == 2
        assert history[1]["attempt"] == 2

    def test_is_non_recoverable(self, retry_mgr):
        assert retry_mgr._is_non_recoverable("") is False
        assert retry_mgr._is_non_recoverable("ValidationError: invalid field") is True
        assert retry_mgr._is_non_recoverable("AuthorizationError: denied") is True
        assert retry_mgr._is_non_recoverable("TimeoutError: slow") is False

    def test_zero_max_retries(self, retry_mgr):
        job = _make_job(attempts=0, max_retries=0)
        decision = retry_mgr.should_retry(job, error="SomeError")
        assert decision.should_retry is False
        assert decision.send_to_dead_letter is True
