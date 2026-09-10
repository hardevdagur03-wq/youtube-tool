from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompt_management.prompt_analytics import PromptAnalyticsCollector
from prompt_management.prompt_models import PromptMetadata
from prompt_management.prompt_repository import PromptRepository


@pytest.fixture
def collector():
    with tempfile.TemporaryDirectory() as tmp:
        repo = PromptRepository(Path(tmp) / "prompts")
        yield PromptAnalyticsCollector(repo)


class TestPromptAnalyticsCollector:
    def test_record_execution(self, collector):
        record = collector.record_execution(
            prompt_id="p_test",
            version="1.0.0",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=250.0,
            success=True,
            quality_score=0.85,
            model_used="gemini-2.0-flash",
        )
        assert record.prompt_id == "p_test"
        assert record.execution_count == 1
        assert record.total_tokens == 150
        assert record.success_count == 1
        assert record.failure_count == 0

    def test_record_failed_execution(self, collector):
        record = collector.record_execution(
            prompt_id="p_test",
            version="1.0.0",
            prompt_tokens=100,
            completion_tokens=0,
            latency_ms=5000.0,
            success=False,
            quality_score=0.0,
            model_used="gemini-2.0-flash",
        )
        assert record.success_count == 0
        assert record.failure_count == 1
        assert record.success_rate == 0.0

    def test_get_summary_empty(self, collector):
        summary = collector.get_summary("nonexistent")
        assert summary["total_executions"] == 0

    def test_get_summary(self, collector):
        collector.record_execution(prompt_id="p_test", version="1.0.0", prompt_tokens=100, completion_tokens=50, latency_ms=200.0, success=True, quality_score=0.9, model_used="gemini-2.0-flash")
        collector.record_execution(prompt_id="p_test", version="1.0.0", prompt_tokens=80, completion_tokens=40, latency_ms=300.0, success=True, quality_score=0.8, model_used="gemini-2.0-flash")
        summary = collector.get_summary("p_test")
        assert summary["total_executions"] == 2
        assert summary["success_rate"] == 1.0
        assert summary["avg_latency_ms"] == 250.0
        assert summary["avg_quality_score"] == pytest.approx(0.85, rel=1e-3)

    def test_get_model_performance(self, collector):
        repo = collector._repository
        repo.save_metadata(PromptMetadata(name="P1", prompt_id="p_1"))
        repo.save_metadata(PromptMetadata(name="P2", prompt_id="p_2"))
        collector.record_execution(prompt_id="p_1", version="1.0.0", prompt_tokens=100, completion_tokens=50, latency_ms=200.0, success=True, quality_score=0.9, model_used="gemini-2.0-flash")
        collector.record_execution(prompt_id="p_2", version="1.0.0", prompt_tokens=100, completion_tokens=50, latency_ms=400.0, success=False, quality_score=0.0, model_used="gemini-2.0-flash")
        perf = collector.get_model_performance("gemini-2.0-flash")
        assert perf["total_executions"] == 2

    def test_get_global_stats(self, collector):
        collector.record_execution(prompt_id="p_1", version="1.0.0", prompt_tokens=100, completion_tokens=50, latency_ms=200.0, success=True, quality_score=0.9, model_used="gemini-2.0-flash")
        collector.record_execution(prompt_id="p_2", version="1.0.0", prompt_tokens=100, completion_tokens=50, latency_ms=400.0, success=False, quality_score=0.0, model_used="gemini-2.0-flash")

        meta1 = PromptMetadata(name="P1", prompt_id="p_1")
        repo = collector._repository
        repo.save_metadata(meta1)
        meta2 = PromptMetadata(name="P2", prompt_id="p_2")
        repo.save_metadata(meta2)

        stats = collector.get_global_stats()
        assert stats["total_prompts"] == 2

    def test_estimate_cost(self, collector):
        cost = collector._estimate_cost(1000, "gemini-2.0-flash")
        assert cost == pytest.approx(0.0001, rel=1e-3)
        cost = collector._estimate_cost(1000, "gpt-4o")
        assert cost == pytest.approx(0.0025, rel=1e-3)
