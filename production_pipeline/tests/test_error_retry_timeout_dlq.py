"""Tests for Error Handler, Retry Framework, Timeout Manager, and DLQ."""

from __future__ import annotations

import pytest

from production_pipeline.error_handler import ErrorHandler, classify_error
from production_pipeline.retry_framework import RetryFramework
from production_pipeline.timeout_manager import TimeoutManager
from production_pipeline.dead_letter_queue import PipelineDeadLetterQueue
from production_pipeline.constants import ErrorClass
from production_pipeline.exceptions import TimeoutError as PipelineTimeoutError


class TestErrorHandler:
    def test_classify_rate_limit(self):
        cls, retry, rec = classify_error(Exception("rate limit exceeded"))
        assert cls == ErrorClass.AI
        assert retry == True

    def test_classify_timeout(self):
        cls, retry, rec = classify_error(Exception("operation timed out"))
        assert cls == ErrorClass.TIMEOUT
        assert retry == True

    def test_classify_database(self):
        cls, retry, rec = classify_error(Exception("database connection refused"))
        assert cls == ErrorClass.DATABASE
        assert retry == True

    def test_classify_network(self):
        cls, retry, rec = classify_error(Exception("socket connection failed"))
        assert cls == ErrorClass.NETWORK

    def test_classify_validation(self):
        cls, retry, rec = classify_error(ValueError("validation failed: invalid input"))
        assert cls == ErrorClass.VALIDATION
        assert retry == False

    def test_classify_auth(self):
        cls, retry, rec = classify_error(Exception("API key is invalid"))
        assert cls == ErrorClass.EXTERNAL_API
        assert retry == False

    def test_classify_unknown(self):
        cls, retry, rec = classify_error(Exception("random unexpected error"))
        assert cls == ErrorClass.UNKNOWN
        assert retry == False

    def test_classify_429(self):
        cls, retry, rec = classify_error(Exception("429 Too Many Requests"))
        assert cls == ErrorClass.AI
        assert retry == True

    def test_handle_returns_safe_message(self):
        response = ErrorHandler.handle(Exception("error"), "stage1", "e1")
        assert "Traceback" not in response["message"]
        assert response["stage"] == "stage1"

    def test_is_retryable(self):
        assert ErrorHandler.is_retryable(Exception("timeout error")) == True
        assert ErrorHandler.is_retryable(ValueError("invalid")) == False

    def test_is_recoverable(self):
        assert ErrorHandler.is_recoverable(Exception("database connection refused")) == True
        assert ErrorHandler.is_recoverable(ValueError("invalid")) == False

    def test_clear_cache(self):
        ErrorHandler.handle(Exception("rate limit"), "s")
        ErrorHandler.clear_cache()


class TestRetryFramework:
    def setup_method(self):
        self.rf = RetryFramework()

    def test_ai_error_retries(self):
        should, delay, reason = self.rf.should_retry(Exception("rate limit"), attempt=1)
        assert should == True
        assert delay > 0

    def test_validation_error_no_retry(self):
        should, _, _ = self.rf.should_retry(ValueError("invalid input"), attempt=1)
        assert should == False

    def test_max_retries_exceeded(self):
        should, _, _ = self.rf.should_retry(Exception("rate limit"), attempt=4)
        assert should == False

    def test_exponential_backoff(self):
        r1, d1, _ = self.rf.should_retry(Exception("timeout"), attempt=1)
        r2, d2, _ = self.rf.should_retry(Exception("timeout"), attempt=2)
        assert r1 == True
        assert r2 == True
        assert d1 > 0
        assert d2 > 0
        # Third attempt should not retry (max 2 for timeout)
        r3, d3, _ = self.rf.should_retry(Exception("timeout"), attempt=3)
        assert r3 == False

    def test_get_policy(self):
        policy = self.rf.get_policy(ErrorClass.AI)
        assert policy["max_retries"] == 3
        assert policy["base_delay"] > 0

    def test_set_policy(self):
        self.rf.set_policy(ErrorClass.AI, {"max_retries": 1, "base_delay": 0.5})
        policy = self.rf.get_policy(ErrorClass.AI)
        assert policy["max_retries"] == 1

    def test_execute_with_retry_success(self):
        def fn():
            return "ok"
        success, result, _, _ = self.rf.execute_with_retry(fn)
        assert success == True
        assert result == "ok"

    def test_execute_with_retry_failure(self):
        def fn():
            raise Exception("fail")
        success, _, _, _ = self.rf.execute_with_retry(fn)
        assert success == False

    def test_reset_history(self):
        self.rf.should_retry(Exception("err"), attempt=1, execution_id="e1", stage_name="s")
        self.rf.reset_history()


class TestTimeoutManager:
    def setup_method(self):
        self.tm = TimeoutManager()

    def test_metadata_timeout(self):
        assert self.tm.get_timeout("metadata") == 15

    def test_analysis_timeout(self):
        assert self.tm.get_timeout("analysis") == 45

    def test_set_timeout_override(self):
        self.tm.set_timeout("metadata", 30)
        assert self.tm.get_timeout("metadata") == 30

    def test_unknown_stage_default(self):
        assert self.tm.get_timeout("unknown_stage") == 30

    def test_get_timeout_config(self):
        tc = self.tm.get_timeout_config("metadata")
        assert tc.stage_name == "metadata"
        assert tc.timeout_seconds > 0

    def test_get_all_timeouts(self):
        timeouts = self.tm.get_all_timeouts()
        assert "metadata" in timeouts
        assert "transcript" in timeouts
        assert "analysis" in timeouts

    def test_reset_overrides(self):
        self.tm.set_timeout("metadata", 99)
        self.tm.reset_overrides()
        assert self.tm.get_timeout("metadata") == 15

    def test_async_timeout(self):
        import asyncio
        async def slow_fn():
            await asyncio.sleep(0.001)
            return "done"
        result = asyncio.run(
            self.tm.enforce_timeout_async("metadata", slow_fn(), timeout_seconds=5)
        )
        assert result == "done"

    def test_async_timeout_exception(self):
        import asyncio
        async def too_slow():
            await asyncio.sleep(10)
            return "done"
        with pytest.raises(PipelineTimeoutError):
            asyncio.run(
                self.tm.enforce_timeout_async("metadata", too_slow(), timeout_seconds=0.01)
            )


class TestDeadLetterQueue:
    def setup_method(self):
        self.dlq = PipelineDeadLetterQueue()

    def test_send(self):
        r = self.dlq.send("e1", "p1", "analysis", Exception("AI failed"), {"input": "test"})
        assert r.dlq_id is not None
        assert r.recovery_status == "pending"

    def test_get(self):
        r = self.dlq.send("e1", "p1", "s", Exception("err"))
        found = self.dlq.get(r.dlq_id)
        assert found is not None

    def test_get_nonexistent(self):
        assert self.dlq.get("nonexistent") is None

    def test_list(self):
        self.dlq.send("e1", "p1", "s", Exception("e1"))
        self.dlq.send("e2", "p1", "s", Exception("e2"))
        entries = self.dlq.list()
        assert len(entries) == 2

    def test_list_filter_by_status(self):
        r = self.dlq.send("e1", "p1", "s", Exception("err"))
        self.dlq.mark_recovered(r.dlq_id)
        pending = self.dlq.list(status="pending")
        recovered = self.dlq.list(status="recovered")
        assert len(pending) == 0
        assert len(recovered) == 1

    def test_count(self):
        self.dlq.send("e1", "p1", "s", Exception("e1"))
        assert self.dlq.count() == 1

    def test_replay(self):
        r = self.dlq.send("e1", "p1", "s", Exception("err"))
        assert self.dlq.replay(r.dlq_id) == True
        assert self.dlq.get(r.dlq_id).retry_count == 0

    def test_replay_nonexistent(self):
        assert self.dlq.replay("nonexistent") == False

    def test_replay_all(self):
        self.dlq.send("e1", "p1", "s", Exception("e1"))
        self.dlq.send("e2", "p1", "s", Exception("e2"))
        count = self.dlq.replay_all()
        assert count == 2

    def test_mark_recovered(self):
        r = self.dlq.send("e1", "p1", "s", Exception("err"))
        assert self.dlq.mark_recovered(r.dlq_id) == True
        assert self.dlq.get(r.dlq_id).recovery_status == "recovered"

    def test_mark_failed(self):
        r = self.dlq.send("e1", "p1", "s", Exception("err"))
        assert self.dlq.mark_failed(r.dlq_id) == True
        assert self.dlq.get(r.dlq_id).recovery_status == "failed"

    def test_purge_all(self):
        self.dlq.send("e1", "p1", "s", Exception("e1"))
        self.dlq.send("e2", "p1", "s", Exception("e2"))
        count = self.dlq.purge()
        assert count == 2
        assert self.dlq.count() == 0

    def test_purge_by_status(self):
        r = self.dlq.send("e1", "p1", "s", Exception("e1"))
        self.dlq.mark_recovered(r.dlq_id)
        count = self.dlq.purge(status="recovered")
        assert count == 1

    def test_export(self):
        self.dlq.send("e1", "p1", "s", Exception("err"), retry_count=3)
        exported = self.dlq.export()
        assert len(exported) == 1
        assert exported[0]["error_class"] is not None
