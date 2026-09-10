"""Performance tests for the DAG Pipeline Engine and Concurrency Framework."""

from __future__ import annotations

import asyncio
import time

import pytest

from services.pipeline.dag_engine import DAGPipelineEngine, StageResult, StageStatus
from services.pipeline.concurrency import (
    AIConcurrencyManager,
    ConcurrencyEngine,
    ConcurrentResult,
    TaskGroup,
)


class TestDAGPipelineEngine:
    @pytest.mark.asyncio
    async def test_single_stage_execution(self):
        engine = DAGPipelineEngine()

        async def stage_a(ctx):
            return "result_a"

        engine.add_stage("stage_a", stage_a)
        results = await engine.execute()

        assert "stage_a" in results
        assert results["stage_a"].status == StageStatus.COMPLETED
        assert results["stage_a"].data == "result_a"

    @pytest.mark.asyncio
    async def test_sequential_dependency(self):
        engine = DAGPipelineEngine()

        async def stage_a(ctx):
            return "data_a"

        async def stage_b(ctx):
            data_a = ctx.get("stage_a")
            return f"{data_a}_processed"

        engine.add_stage("stage_a", stage_a)
        engine.add_stage("stage_b", stage_b, dependencies=["stage_a"])

        results = await engine.execute()
        assert results["stage_a"].status == StageStatus.COMPLETED
        assert results["stage_b"].status == StageStatus.COMPLETED
        assert results["stage_b"].data == "data_a_processed"

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        engine = DAGPipelineEngine()
        timing = {}

        async def stage_a(ctx):
            timing["a_start"] = time.time()
            await asyncio.sleep(0.02)
            timing["a_end"] = time.time()
            return "a"

        async def stage_b(ctx):
            timing["b_start"] = time.time()
            await asyncio.sleep(0.02)
            timing["b_end"] = time.time()
            return "b"

        engine.add_stage("stage_a", stage_a)
        engine.add_stage("stage_b", stage_b)

        results = await engine.execute()

        assert results["stage_a"].status == StageStatus.COMPLETED
        assert results["stage_b"].status == StageStatus.COMPLETED

        wall_time = max(timing["a_end"], timing["b_end"]) - min(
            timing["a_start"], timing["b_start"]
        )
        assert wall_time < 0.10

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_speedup(self):
        engine = DAGPipelineEngine()

        async def fast_stage(ctx):
            await asyncio.sleep(0.02)
            return "done"

        engine.add_stage("a", fast_stage)
        engine.add_stage("b", fast_stage)
        engine.add_stage("c", fast_stage)

        start = time.time()
        results = await engine.execute()
        elapsed = time.time() - start

        sequential = 0.06
        assert elapsed < sequential + 0.05

    @pytest.mark.asyncio
    async def test_stage_failure(self):
        engine = DAGPipelineEngine()

        async def failing_stage(ctx):
            raise ValueError("Intentional failure")

        engine.add_stage("fail", failing_stage)
        results = await engine.execute()

        assert results["fail"].status == StageStatus.FAILED
        assert "Intentional failure" in results["fail"].error

    @pytest.mark.asyncio
    async def test_stage_retry(self):
        engine = DAGPipelineEngine()
        attempt_count = [0]

        async def retry_stage(ctx):
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise ValueError(f"Attempt {attempt_count[0]} failed")
            return "success"

        engine.add_stage("retry", retry_stage, retries=2)
        results = await engine.execute()

        assert results["retry"].status == StageStatus.COMPLETED
        assert results["retry"].data == "success"
        assert attempt_count[0] == 2

    @pytest.mark.asyncio
    async def test_timeout(self):
        engine = DAGPipelineEngine()

        async def slow_stage(ctx):
            await asyncio.sleep(10)
            return "too_late"

        engine.add_stage("slow", slow_stage, timeout=0.5)
        results = await engine.execute()

        assert results["slow"].status == StageStatus.FAILED
        assert "Timeout" in results["slow"].error

    @pytest.mark.asyncio
    async def test_dependency_chain(self):
        engine = DAGPipelineEngine()
        execution_order = []

        async def a(ctx):
            execution_order.append("a")
            return 1

        async def b(ctx):
            execution_order.append("b")
            return ctx["a"] + 1

        async def c(ctx):
            execution_order.append("c")
            return ctx["b"] + 1

        engine.add_stage("a", a)
        engine.add_stage("b", b, dependencies=["a"])
        engine.add_stage("c", c, dependencies=["b"])

        results = await engine.execute()

        assert execution_order == ["a", "b", "c"]
        assert results["c"].data == 3

    @pytest.mark.asyncio
    async def test_diamond_dependency(self):
        engine = DAGPipelineEngine()

        async def root(ctx):
            return "root"

        async def left(ctx):
            return f"{ctx['root']}_left"

        async def right(ctx):
            return f"{ctx['root']}_right"

        async def merge(ctx):
            return f"{ctx['left']}_{ctx['right']}"

        engine.add_stage("root", root)
        engine.add_stage("left", left, dependencies=["root"])
        engine.add_stage("right", right, dependencies=["root"])
        engine.add_stage("merge", merge, dependencies=["left", "right"])

        start = time.time()
        results = await engine.execute()
        elapsed = (time.time() - start) * 1000

        assert results["merge"].data == "root_left_root_right"
        assert results["left"].status == StageStatus.COMPLETED
        assert results["right"].status == StageStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_context_sharing(self):
        engine = DAGPipelineEngine()

        async def writer(ctx):
            ctx["shared"] = "written"
            return "ok"

        async def reader(ctx):
            return ctx.get("shared", "not_found")

        engine.add_stage("writer", writer)
        engine.add_stage("reader", reader, dependencies=["writer"])

        results = await engine.execute()
        assert results["reader"].data == "written"

    @pytest.mark.asyncio
    async def test_summary_output(self):
        engine = DAGPipelineEngine()

        async def stage(ctx):
            return "ok"

        engine.add_stage("test", stage)
        results = await engine.execute()
        summary = engine.summary(results)

        assert "total_stages" in summary
        assert "completed" in summary
        assert "failed" in summary
        assert "stages" in summary
        assert summary["completed"] == 1

    @pytest.mark.asyncio
    async def test_empty_pipeline(self):
        engine = DAGPipelineEngine()
        results = await engine.execute()
        assert results == {}

    @pytest.mark.asyncio
    async def test_get_stage(self):
        engine = DAGPipelineEngine()
        async def fn(ctx): pass
        engine.add_stage("test", fn)
        node = engine.get_stage("test")
        assert node is not None
        assert node.name == "test"
        assert engine.get_stage("nonexistent") is None

    @pytest.mark.asyncio
    async def test_context_methods(self):
        engine = DAGPipelineEngine()
        engine.set_context("key", "value")
        assert engine.get_context("key") == "value"
        assert engine.get_context("missing", "default") == "default"


class TestConcurrencyEngine:
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        engine = ConcurrencyEngine(max_concurrent=10)
        timing = {}

        async def task_a():
            timing["a"] = time.time()
            await asyncio.sleep(0.05)
            return "a"

        async def task_b():
            timing["b"] = time.time()
            await asyncio.sleep(0.05)
            return "b"

        results = await engine.execute_all({
            "a": task_a,
            "b": task_b,
        })

        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_task_failure_isolated(self):
        engine = ConcurrencyEngine(max_concurrent=5)

        async def good():
            return "ok"

        async def bad():
            raise ValueError("Task failed")

        results = await engine.execute_all({
            "good": good,
            "bad": bad,
        })

        for r in results:
            if r.name == "good":
                assert r.success is True
            if r.name == "bad":
                assert r.success is False

    @pytest.mark.asyncio
    async def test_max_concurrent_limit(self):
        engine = ConcurrencyEngine(max_concurrent=2)
        running = [0]
        max_running = [0]

        async def task():
            running[0] += 1
            max_running[0] = max(max_running[0], running[0])
            await asyncio.sleep(0.05)
            running[0] -= 1
            return "ok"

        tasks = {f"t{i}": task for i in range(10)}
        await engine.execute_all(tasks)

        assert max_running[0] <= 2

    @pytest.mark.asyncio
    async def test_speedup_over_sequential(self):
        engine = ConcurrencyEngine(max_concurrent=10)
        sleep_time = 0.05

        async def slow_task():
            await asyncio.sleep(sleep_time)
            return "done"

        tasks = {f"t{i}": slow_task for i in range(5)}
        start = time.time()
        results = await engine.execute_all(tasks)
        elapsed = time.time() - start

        sequential = sleep_time * 5
        assert elapsed < sequential * 0.6
        assert all(r.success for r in results)


class TestTaskGroup:
    @pytest.mark.asyncio
    async def test_group_execution(self):
        group = TaskGroup()

        async def task_a():
            await asyncio.sleep(0.02)
            return "A"

        async def task_b():
            await asyncio.sleep(0.02)
            return "B"

        group.add("a", task_a)
        group.add("b", task_b)

        results = await group.run(max_concurrent=5)
        assert results["a"].success is True
        assert results["b"].success is True


class TestAIConcurrencyManager:
    @pytest.mark.asyncio
    async def test_parallel_ai_tasks(self):
        mgr = AIConcurrencyManager(max_concurrent=5)

        async def seo():
            await asyncio.sleep(0.03)
            return {"score": 85}

        async def kg():
            await asyncio.sleep(0.02)
            return {"entities": 10}

        async def entities():
            await asyncio.sleep(0.01)
            return ["entity1"]

        results = await mgr.run_ai_tasks({
            "seo": seo,
            "kg": kg,
            "entities": entities,
        })

        assert results["seo"].success is True
        assert results["kg"].success is True
        assert results["entities"].success is True

    @pytest.mark.asyncio
    async def test_ai_speedup(self):
        mgr = AIConcurrencyManager(max_concurrent=5)

        async def slow_ai():
            await asyncio.sleep(0.1)
            return "done"

        tasks = {f"ai_{i}": slow_ai for i in range(4)}
        start = time.time()
        results = await mgr.run_ai_tasks(tasks)
        elapsed = time.time() - start

        assert elapsed < 0.3
        assert all(r.success for r in results.values())

    @pytest.mark.asyncio
    async def test_summary(self):
        mgr = AIConcurrencyManager(max_concurrent=5)

        async def task():
            await asyncio.sleep(0.01)
            return "ok"

        results = await mgr.run_ai_tasks({"t1": task, "t2": task})
        summary = mgr.summary(results)

        assert summary["total_tasks"] == 2
        assert summary["succeeded"] == 2
        assert summary["speedup"] >= 1.0
        assert summary["time_saved_ms"] >= 0


class TestConcurrentResult:
    def test_default_values(self):
        r = ConcurrentResult()
        assert r.success is False
        assert r.name == ""
        assert r.error == ""

    def test_success_result(self):
        r = ConcurrentResult(name="test", success=True, data="result", duration_ms=10.5)
        assert r.name == "test"
        assert r.data == "result"
        assert r.duration_ms == 10.5


class TestStageResult:
    def test_default_values(self):
        r = StageResult()
        assert r.status == StageStatus.PENDING
        assert r.name == ""

    def test_completed_result(self):
        r = StageResult(
            name="test",
            status=StageStatus.COMPLETED,
            duration_ms=100.0,
            data="output",
        )
        assert r.name == "test"
        assert r.data == "output"
