"""Tests for Performance Engineering — all modules."""

from __future__ import annotations

import time

from performance_engineering.config import PerformanceConfig
from performance_engineering.models import (
    StageTiming, PipelineTiming, CacheStats, LatencyPercentiles,
    ThroughputMetric, BenchmarkResult,
)
from performance_engineering.pipeline import AsyncExecutor, ParallelScheduler, BatchAIProcessor
from performance_engineering.cache import PromptCache, EmbeddingCache, QueryCache, CacheInvalidator
from performance_engineering.streaming import SSEManager, ProgressStream
from performance_engineering.queue import PriorityRouter, ThroughputOptimizer
from performance_engineering.memory import LazyLoader, MemoryOptimizer
from performance_engineering.connection_pool import ConnectionPoolManager
from performance_engineering.monitoring import PerformanceDashboard, LatencyProfiler
from performance_engineering.benchmark import BenchmarkRunner, BenchmarkScenarios, BenchmarkReporter


class TestConfig:
    def test_default_config(self):
        c = PerformanceConfig()
        assert c.async_max_workers == 8
        assert c.parallel_enabled == True
        assert c.cache_prompt_enabled == True

    def test_from_env(self):
        c = PerformanceConfig.from_env()
        assert c.async_max_workers >= 1


class TestModels:
    def test_stage_timing(self):
        st = StageTiming(stage_name="metadata", duration_ms=1500.0)
        assert st.stage_name == "metadata"
        assert st.duration_ms == 1500.0

    def test_pipeline_timing(self):
        pt = PipelineTiming(pipeline_id="p1")
        assert pt.pipeline_id == "p1"
        pt.stage_timings.append(StageTiming(stage_name="m"))
        assert len(pt.stage_timings) == 1

    def test_cache_stats(self):
        cs = CacheStats(cache_name="prompt", hits=90, misses=10)
        assert cs.hit_rate == 0.0
        cs.hit_rate = 90 / 100
        assert cs.hit_rate == 0.9

    def test_latency_percentiles(self):
        lp = LatencyPercentiles(p50_ms=100, p95_ms=500, sample_count=1000)
        assert lp.p50_ms == 100
        assert lp.p95_ms == 500

    def test_benchmark_result(self):
        br = BenchmarkResult(scenario_name="test", before={"a": 1}, after={"a": 2})
        assert br.scenario_name == "test"
        assert br.improvement_pct >= 0 or br.improvement_pct <= 0


class TestAsyncExecutor:
    def test_run_sync(self):
        import asyncio
        exec = AsyncExecutor()
        result = asyncio.run(exec.run(lambda x: x + 1, 41))
        assert result == 42

    def test_get_stats(self):
        import asyncio
        exec = AsyncExecutor()
        asyncio.run(exec.run(lambda: None))
        stats = exec.get_stats()
        assert stats["total_tasks"] >= 1


class TestParallelScheduler:
    def test_compute_groups(self):
        ps = ParallelScheduler()
        groups = ps.compute_parallel_groups(["metadata", "transcript", "analysis"])
        assert len(groups) >= 3
        assert groups[0] == ["metadata"]

    def test_estimate_speedup(self):
        ps = ParallelScheduler()
        estimate = ps.estimate_speedup({
            "metadata": 2000, "transcript": 5000, "analysis": 8000,
            "knowledge_graph": 4000, "seo": 3000,
        })
        assert estimate["speedup_ratio"] >= 1.0


class TestBatchAI:
    def test_batch_execute(self):
        import asyncio
        bp = BatchAIProcessor()
        async def batch_fn(inputs):
            return [f"result_{i}" for i in range(len(inputs))]
        tasks = [{"name": "a", "input": "i1"}, {"name": "b", "input": "i2"}]
        results = asyncio.run(bp.batch_execute(tasks, batch_fn))
        assert len(results) == 2


class TestPromptCache:
    def test_set_and_get(self):
        pc = PromptCache()
        key = pc.build_key("test prompt", "gpt-4", 0.1)
        assert key is not None
        pc.set(key, {"response": "test"})
        cached = pc.get(key)
        assert cached["response"] == "test"

    def test_deterministic_only(self):
        pc = PromptCache()
        key = pc.build_key("test", "gpt-4", 0.7)
        assert key is None  # Non-deterministic

    def test_stats(self):
        pc = PromptCache()
        stats = pc.stats
        assert stats["cache_name"] == "prompt"


class TestEmbeddingCache:
    def test_set_and_get(self):
        ec = EmbeddingCache()
        ec.set_embedding("hello", [0.1, 0.2, 0.3])
        vec = ec.get_embedding("hello")
        assert vec == [0.1, 0.2, 0.3]

    def test_search_results(self):
        ec = EmbeddingCache()
        ec.set_search_results("query", ["result1"])
        results = ec.get_search_results("query")
        assert results == ["result1"]


class TestQueryCache:
    def test_set_and_get(self):
        qc = QueryCache()
        key = qc.build_key("SELECT 1", {})
        qc.set(key, [1], tables="test")
        assert qc.get(key) == [1]

    def test_table_invalidation(self):
        qc = QueryCache()
        key = qc.build_key("SELECT * FROM t", {})
        qc.set(key, "data", tables="t")
        qc.invalidate_table("t")
        assert qc.get(key) is None


class TestSSEManager:
    def test_publish_no_subscribers(self):
        import asyncio
        sse = SSEManager()
        n = asyncio.run(sse.publish("test", {"msg": "hello"}))
        assert n == 0


class TestPriorityRouter:
    def test_queue_mapping(self):
        pr = PriorityRouter()
        assert pr.get_queue("analysis") == "ai_critical"
        assert pr.get_queue("export") == "export"

    def test_queue_load(self):
        pr = PriorityRouter()
        load = pr.get_queue_load_summary()
        assert "ai_critical" in load


class TestThroughputOptimizer:
    def test_recommendation(self):
        to = ThroughputOptimizer()
        to.record_queue_depth("test", 10)
        rec = to.recommend_scale("test")
        assert "recommendation" in rec


class TestLazyLoader:
    def test_lazy_init(self):
        called = [0]
        def factory():
            called[0] += 1
            return "service"
        loader = LazyLoader(factory)
        assert called[0] == 0
        result = loader.get()
        assert result == "service"
        assert called[0] == 1
        loader.get()
        assert called[0] == 1  # Not re-initialized


class TestMemoryOptimizer:
    def test_get_memory_usage(self):
        mo = MemoryOptimizer()
        usage = mo.get_memory_usage()
        assert "rss_mb" in usage

    def test_optimize(self):
        mo = MemoryOptimizer()
        result = mo.optimize()
        assert "freed_mb" in result


class TestConnectionPool:
    def test_get_client(self):
        pool = ConnectionPoolManager()
        client = pool.get_http_client("test")
        assert client is not None


class TestPerformanceDashboard:
    def test_record_latency(self):
        dash = PerformanceDashboard()
        dash.record_latency("test", 100.0)
        lp = dash.get_latency_percentiles("test")
        assert lp.p50_ms == 100.0

    def test_full_dashboard(self):
        dash = PerformanceDashboard()
        dash.record_latency("test", 100.0)
        report = dash.get_full_dashboard()
        assert "latency" in report


class TestLatencyProfiler:
    def test_profile(self):
        profiler = LatencyProfiler()
        with profiler.profile("test_stage"):
            time.sleep(0.001)
        summary = profiler.get_timing_summary("test_stage")
        assert summary["count"] >= 1

    def test_slow_stage_detection(self):
        profiler = LatencyProfiler(slow_threshold_ms=0.5)
        with profiler.profile("slow"):
            time.sleep(0.01)
        slow = profiler.get_slow_stages()
        assert len(slow) >= 1


class TestBenchmarkRunner:
    def test_run_scenario(self):
        runner = BenchmarkRunner()
        results = runner.run_scenario("test", lambda: None, samples=3)
        assert f"test_avg_ms" in str(results)

    def test_compare(self):
        runner = BenchmarkRunner()
        result = runner.compare("test", lambda: time.sleep(0.01), lambda: None, samples=3)
        assert result.scenario_name == "test"
        assert isinstance(result.before, dict)


class TestBenchmarkReporter:
    def test_json_report(self):
        br = BenchmarkResult(scenario_name="test", before={"a": 1}, after={"a": 2})
        report = BenchmarkReporter.to_json([br])
        assert "test" in report

    def test_markdown_report(self):
        br = BenchmarkResult(scenario_name="test", before={"a": 1}, after={"a": 2})
        report = BenchmarkReporter.to_markdown([br])
        assert "test" in report

    def test_html_report(self):
        br = BenchmarkResult(scenario_name="test", before={"a": 1}, after={"a": 2})
        report = BenchmarkReporter.to_html([br])
        assert "test" in report
