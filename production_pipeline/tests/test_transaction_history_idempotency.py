"""Tests for Transaction Logger, Execution History, and Idempotency."""

from __future__ import annotations

from production_pipeline.transaction_logger import TransactionLogger
from production_pipeline.execution_history import ExecutionHistory
from production_pipeline.idempotency import IdempotencyFramework


class TestTransactionLogger:
    def setup_method(self):
        self.tl = TransactionLogger()

    def test_log_event(self):
        e = self.tl.log_event("e1", "stage_started", "metadata", "running")
        assert e.action == "stage_started"
        assert e.execution_id == "e1"
        assert e.event_id is not None

    def test_log_event_with_full_context(self):
        e = self.tl.log_event("e1", "stage_completed", "transcript", "completed",
                               request_id="r1", correlation_id="c1", trace_id="t1",
                               worker_id="w1", duration_ms=1500, retry_count=2,
                               error="", details={"key": "val"})
        assert e.request_id == "r1"
        assert e.correlation_id == "c1"
        assert e.duration_ms == 1500
        assert e.retry_count == 2

    def test_get_events(self):
        self.tl.log_event("e1", "a", status="ok")
        self.tl.log_event("e1", "b", status="ok")
        events = self.tl.get_events("e1")
        assert len(events) == 2

    def test_get_events_empty(self):
        events = self.tl.get_events("nonexistent")
        assert events == []

    def test_get_events_by_correlation(self):
        self.tl.log_event("e1", "a", correlation_id="c1")
        events = self.tl.get_events_by_correlation("c1")
        assert len(events) == 1

    def test_get_events_by_action(self):
        self.tl.log_event("e1", "stage_started")
        self.tl.log_event("e1", "stage_completed")
        started = self.tl.get_events_by_action("stage_started")
        assert len(started) == 1

    def test_get_all_events(self):
        self.tl.log_event("e1", "a")
        self.tl.log_event("e2", "b")
        all_e = self.tl.get_all_events()
        assert len(all_e) == 2

    def test_get_event_count(self):
        self.tl.log_event("e1", "a")
        self.tl.log_event("e1", "b")
        assert self.tl.get_event_count("e1") == 2
        assert self.tl.get_event_count() == 2

    def test_get_timeline(self):
        self.tl.log_event("e1", "started", status="running", duration_ms=100)
        self.tl.log_event("e1", "completed", status="completed", duration_ms=200)
        timeline = self.tl.get_timeline("e1")
        assert len(timeline) == 2
        assert timeline[0]["action"] == "started"
        assert timeline[1]["action"] == "completed"

    def test_clear(self):
        self.tl.log_event("e1", "a")
        self.tl.clear()
        assert self.tl.get_event_count() == 0

    def test_multiple_executions_independent(self):
        self.tl.log_event("e1", "a")
        self.tl.log_event("e2", "b")
        assert len(self.tl.get_events("e1")) == 1
        assert len(self.tl.get_events("e2")) == 1


class TestExecutionHistory:
    def setup_method(self):
        self.tl = TransactionLogger()
        self.eh = ExecutionHistory(self.tl)

    def test_get_timeline(self):
        self.tl.log_event("e1", "started", status="running")
        self.tl.log_event("e1", "completed", status="completed")
        timeline = self.eh.get_timeline("e1")
        assert len(timeline) == 2

    def test_get_stage_timeline(self):
        self.tl.log_event("e1", "stage_started", "metadata", "running")
        self.tl.log_event("e1", "stage_completed", "metadata", "completed")
        self.tl.log_event("e1", "stage_started", "transcript", "running")
        stages = self.eh.get_stage_timeline("e1", "metadata")
        assert len(stages) == 2

    def test_compare_executions(self):
        self.tl.log_event("e1", "a", "metadata", "completed")
        self.tl.log_event("e2", "a", "transcript", "completed")
        cmp = self.eh.compare_executions("e1", "e2")
        assert "stages_only_in_a" in cmp
        assert "common_stages" in cmp

    def test_get_summary(self):
        self.tl.log_event("e1", "started", status="running", duration_ms=100)
        self.tl.log_event("e1", "completed", status="completed", duration_ms=200)
        summary = self.eh.get_summary("e1")
        assert summary["total_events"] == 2
        assert summary["total_duration_ms"] > 0

    def test_summary_empty(self):
        summary = self.eh.get_summary("nonexistent")
        assert summary["events"] == 0

    def test_query_by_execution(self):
        self.tl.log_event("e1", "a")
        self.tl.log_event("e2", "b")
        results = self.eh.query(execution_id="e1")
        assert len(results) == 1

    def test_query_by_action(self):
        self.tl.log_event("e1", "stage_started")
        self.tl.log_event("e1", "stage_completed")
        results = self.eh.query(action="stage_started")
        assert len(results) == 1

    def test_query_by_stage_and_status(self):
        self.tl.log_event("e1", "a", "metadata", "running")
        self.tl.log_event("e1", "b", "metadata", "completed")
        results = self.eh.query(stage_name="metadata", status="running")
        assert len(results) == 1


class TestIdempotency:
    def setup_method(self):
        self.idf = IdempotencyFramework()

    def test_register_new_key(self):
        is_dup, existing, warning = self.idf.check_and_register("e1", "metadata", {"url": "x"})
        assert is_dup == False
        assert existing is None
        assert warning is None

    def test_detect_duplicate(self):
        self.idf.check_and_register("e1", "metadata", {"url": "x"})
        self.idf.mark_completed("e1", "metadata", {"url": "x"}, {"title": "T"})
        is_dup, existing, warning = self.idf.check_and_register("e1", "metadata", {"url": "x"})
        assert is_dup == True
        assert existing is not None
        assert "already completed" in warning

    def test_different_stages_no_dup(self):
        self.idf.check_and_register("e1", "metadata", {"url": "x"})
        is_dup, _, _ = self.idf.check_and_register("e1", "transcript", {"text": "y"})
        assert is_dup == False

    def test_different_inputs_no_dup(self):
        self.idf.check_and_register("e1", "metadata", {"url": "x"})
        is_dup, _, _ = self.idf.check_and_register("e1", "metadata", {"url": "y"})
        assert is_dup == False

    def test_mark_completed(self):
        self.idf.check_and_register("e1", "m", {"i": 1})
        self.idf.mark_completed("e1", "m", {"i": 1}, {"o": 1})
        key = self.idf.get_key("e1", "m", {"i": 1})
        assert key.status == "completed"

    def test_mark_failed_allows_retry(self):
        self.idf.check_and_register("e1", "m", {"i": 1})
        self.idf.mark_failed("e1", "m", {"i": 1})
        is_dup, _, _ = self.idf.check_and_register("e1", "m", {"i": 1})
        assert is_dup == False

    def test_check_duplicate(self):
        self.idf.check_and_register("e1", "m", {"i": 1})
        self.idf.mark_completed("e1", "m", {"i": 1}, {})
        assert self.idf.check_duplicate("e1", "m", {"i": 1}) == True

    def test_is_running(self):
        self.idf.check_and_register("e1", "m", {"i": 1})
        assert self.idf.is_running("e1", "m", {"i": 1}) == True
        self.idf.mark_completed("e1", "m", {"i": 1}, {})
        assert self.idf.is_running("e1", "m", {"i": 1}) == False

    def test_get_key_none(self):
        key = self.idf.get_key("e1", "nonexistent", {})
        assert key is None

    def test_clear(self):
        self.idf.check_and_register("e1", "m", {"i": 1})
        self.idf.clear()
        assert self.idf.get_stats()["total_keys"] == 0

    def test_get_stats(self):
        self.idf.check_and_register("e1", "m1", {"i": 1})
        self.idf.check_and_register("e2", "m2", {"i": 2})
        stats = self.idf.get_stats()
        assert stats["total_keys"] == 2
        assert stats["running"] == 2

    def test_deterministic_key(self):
        k1 = self.idf._build_key("e1", "m", "hash123")
        k2 = self.idf._build_key("e1", "m", "hash123")
        assert k1 == k2

    def test_key_changes_with_input(self):
        self.idf.check_and_register("e1", "m", {"i": 1})
        self.idf.mark_completed("e1", "m", {"i": 1}, {})
        is_dup, _, _ = self.idf.check_and_register("e1", "m", {"i": 2})
        assert is_dup == False
