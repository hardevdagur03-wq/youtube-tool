"""Tests for the Pipeline Orchestrator.

All existing tests continue to work unchanged.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.pipeline_events import EventBus, PipelineEvent, PipelineEventType
from orchestrator.pipeline_state import PipelineState, StageState, StageInfo
from orchestrator.execution_graph import ExecutionGraph, GraphNode
from orchestrator.dependency_resolver import DependencyResolver
from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.stage_registry import StageRegistry
from orchestrator.pipeline_context import PipelineContext
from orchestrator.retry_manager import RetryManager, RetryPolicy
from orchestrator.error_handler import ErrorHandler, PipelineError
from orchestrator.progress_emitter import ProgressEmitter
from orchestrator.cache_manager import CacheManager
from orchestrator.pipeline_metrics import PipelineMetrics
from orchestrator.pipeline_controller import PipelineController
from orchestrator.pipeline_orchestrator import PipelineOrchestrator
from projects.project_manager import ProjectManager


# ---------------------------------------------------------------------------
# Pipeline Events / Event Bus
# ---------------------------------------------------------------------------


class TestEventBus:
    @pytest.mark.asyncio
    async def test_emit_and_subscribe(self):
        bus = EventBus()
        received = []

        async def handler(event: PipelineEvent):
            received.append(event)

        bus.subscribe(PipelineEventType.PIPELINE_STARTED, handler)
        await bus.emit(PipelineEvent(
            type=PipelineEventType.PIPELINE_STARTED,
            project_id="test123",
            message="Test event",
        ))
        assert len(received) == 1
        assert received[0].type == PipelineEventType.PIPELINE_STARTED

    @pytest.mark.asyncio
    async def test_global_subscriber(self):
        bus = EventBus()
        received = []

        async def handler(event: PipelineEvent):
            received.append(event)

        bus.subscribe_all(handler)
        await bus.emit(PipelineEvent(
            type=PipelineEventType.STAGE_STARTED, project_id="p1",
        ))
        await bus.emit(PipelineEvent(
            type=PipelineEventType.STAGE_COMPLETED, project_id="p1",
        ))
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_history(self):
        bus = EventBus()
        await bus.emit(PipelineEvent(type=PipelineEventType.PIPELINE_STARTED, project_id="p1"))
        await bus.emit(PipelineEvent(type=PipelineEventType.PIPELINE_COMPLETED, project_id="p1"))
        history = bus.get_history()
        assert len(history) == 2

    def test_event_types(self):
        assert PipelineEventType.PIPELINE_STARTED.value == "pipeline_started"
        assert PipelineEventType.STAGE_FAILED.value == "stage_failed"


# ---------------------------------------------------------------------------
# Pipeline State / Stage State
# ---------------------------------------------------------------------------


class TestStageState:
    def test_initial_state(self):
        info = StageInfo("test_stage", dependencies=["dep1"])
        assert info.name == "test_stage"
        assert info.state == StageState.WAITING
        assert info.dependencies == ["dep1"]

    def test_valid_transitions(self):
        info = StageInfo("stage")
        info.transition_to(StageState.READY)
        assert info.state == StageState.READY
        info.transition_to(StageState.RUNNING)
        assert info.state == StageState.RUNNING
        info.mark_success()
        assert info.state == StageState.SUCCESS

    def test_invalid_transition(self):
        info = StageInfo("stage")
        info.state = StageState.SUCCESS
        with pytest.raises(ValueError):
            info.transition_to(StageState.RUNNING)

    def test_terminal_states(self):
        assert StageState.SUCCESS in StageState.terminal_states()
        assert StageState.FAILED in StageState.terminal_states()
        assert StageState.RUNNING not in StageState.terminal_states()

    def test_failed_then_retry(self):
        info = StageInfo("stage")
        info.transition_to(StageState.READY)
        info.mark_running()
        info.mark_failed("error")
        assert info.state == StageState.FAILED
        info.transition_to(StageState.READY)
        assert info.state == StageState.READY

    def test_to_dict(self):
        info = StageInfo("test", dependencies=["a"])
        d = info.to_dict()
        assert d["name"] == "test"
        assert d["state"] == "waiting"


class TestPipelineState:
    def test_transitions(self):
        state = PipelineState.NOT_STARTED
        assert state.can_transition_to(PipelineState.READY)
        assert not state.can_transition_to(PipelineState.COMPLETED)

    def test_terminal(self):
        assert PipelineState.COMPLETED in PipelineState.terminal_states()
        assert PipelineState.RUNNING not in PipelineState.terminal_states()


# ---------------------------------------------------------------------------
# Execution Graph
# ---------------------------------------------------------------------------


class TestExecutionGraph:
    def test_add_node(self):
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        assert g.get_node("a") is not None
        assert g.get_node("c") is None

    def test_topological_sort(self):
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["b"])
        order = g.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_get_ready_stages(self):
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["a"])
        ready = g.get_ready_stages(set(), set())
        assert "a" in ready

        ready_after_a = g.get_ready_stages({"a"}, set())
        assert "a" not in ready_after_a
        assert "b" in ready_after_a
        assert "c" in ready_after_a

    def test_get_dependents(self):
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["a"])
        deps = g.get_dependents("a")
        assert "b" in deps
        assert "c" in deps

    def test_validate(self):
        g = ExecutionGraph()
        g.add_node("a", ["nonexistent"])
        errors = g.validate()
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_levels(self):
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["a"])
        g.add_node("d", ["b", "c"])
        levels = g.levels()
        assert levels[0] == ["a"]
        assert "d" in levels[-1]


# ---------------------------------------------------------------------------
# Dependency Resolver
# ---------------------------------------------------------------------------


class TestDependencyResolver:
    def test_execution_order(self):
        resolver = DependencyResolver({
            "a": [],
            "b": ["a"],
            "c": ["b"],
        })
        order = resolver.execution_order()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_parallel_levels(self):
        resolver = DependencyResolver({
            "a": [],
            "b": ["a"],
            "c": ["a"],
            "d": ["b", "c"],
        })
        levels = resolver.parallel_levels()
        assert levels[0] == ["a"]
        assert len(levels) == 3

    def test_can_run_in_parallel(self):
        resolver = DependencyResolver({
            "a": [],
            "b": ["a"],
            "c": ["a"],
        })
        assert resolver.can_run_in_parallel("b", "c")
        assert not resolver.can_run_in_parallel("a", "b")

    def test_default_stages(self):
        resolver = DependencyResolver()
        stages = resolver.stages
        assert "metadata" in stages
        assert "transcript" in stages
        assert "analysis" in stages
        assert "export" in stages


# ---------------------------------------------------------------------------
# Stage Executor / Registry
# ---------------------------------------------------------------------------


class TestStageRegistry:
    def test_register_and_get(self):
        registry = StageRegistry()
        executor = MagicMock(spec=StageExecutor)
        executor.name = "test_stage"
        executor.dependencies = []
        registry.register(executor)
        assert registry.get("test_stage") is executor

    def test_names(self):
        registry = StageRegistry()
        e1 = MagicMock(spec=StageExecutor)
        e1.name = "a"
        e1.dependencies = []
        e2 = MagicMock(spec=StageExecutor)
        e2.name = "b"
        e2.dependencies = []
        registry.register(e1)
        registry.register(e2)
        assert "a" in registry.names
        assert "b" in registry.names

    def test_dependency_map(self):
        registry = StageRegistry()
        e1 = MagicMock(spec=StageExecutor)
        e1.name = "a"
        e1.dependencies = []
        e2 = MagicMock(spec=StageExecutor)
        e2.name = "b"
        e2.dependencies = ["a"]
        registry.register(e1)
        registry.register(e2)
        deps = registry.get_dependency_map()
        assert deps["a"] == []
        assert deps["b"] == ["a"]


# ---------------------------------------------------------------------------
# Retry Manager
# ---------------------------------------------------------------------------


class TestRetryManager:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        rm = RetryManager()
        async def succeed():
            return "ok"
        success, result, error, retries = await rm.execute_with_retry("test", succeed)
        assert success
        assert result == "ok"
        assert retries == 0

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        rm = RetryManager(RetryPolicy(max_retries=3, base_delay=0.01))
        attempt = [0]
        async def fail_then_succeed():
            attempt[0] += 1
            if attempt[0] < 2:
                raise ValueError("timeout")
            return "ok"
        success, result, error, retries = await rm.execute_with_retry("test", fail_then_succeed)
        assert success
        assert result == "ok"
        assert retries == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        rm = RetryManager(RetryPolicy(max_retries=2, base_delay=0.01))
        async def always_fail():
            raise ValueError("timeout")
        success, result, error, retries = await rm.execute_with_retry("test", always_fail)
        assert not success
        assert retries == 3

    def test_history(self):
        rm = RetryManager()
        history = rm.get_retry_history("nonexistent")
        assert history == []


# ---------------------------------------------------------------------------
# Error Handler
# ---------------------------------------------------------------------------


class TestErrorHandler:
    def test_classify_timeout(self):
        err = ErrorHandler.classify(Exception("timeout error"))
        assert err.error_type == "timeout"
        assert err.retryable
        assert err.recoverable

    def test_classify_quota(self):
        err = ErrorHandler.classify(Exception("quota exceeded"))
        assert err.error_type == "quota_exceeded"
        assert err.retryable

    def test_classify_channel_not_found(self):
        err = ErrorHandler.classify(Exception("channel not found"))
        assert err.error_type == "channel_not_found"
        assert not err.retryable

    def test_classify_unexpected(self):
        err = ErrorHandler.classify(Exception("some random error"))
        assert err.error_type == "unexpected"
        assert not err.retryable

    def test_should_retry(self):
        assert ErrorHandler.should_retry(PipelineError(error_type="timeout", retryable=True, recoverable=True))
        assert not ErrorHandler.should_retry(PipelineError(error_type="channel_not_found", retryable=False))

    def test_user_message(self):
        msg = ErrorHandler.user_message(PipelineError(error_type="quota_exceeded"))
        assert "quota" in msg

        msg = ErrorHandler.user_message(PipelineError(error_type="channel_not_found"))
        assert "not found" in msg


# ---------------------------------------------------------------------------
# Cache Manager
# ---------------------------------------------------------------------------


class TestCacheManager:
    def test_set_and_get(self):
        cache = CacheManager()
        ctx = PipelineContext(video_id="test123")
        cache.set("metadata", ctx, {"title": "Test"})
        result = cache.get("metadata", ctx)
        assert result is not None
        assert result["title"] == "Test"

    def test_cache_miss(self):
        cache = CacheManager()
        ctx = PipelineContext(video_id="test123")
        result = cache.get("nonexistent", ctx)
        assert result is None

    def test_invalidate(self):
        cache = CacheManager()
        ctx = PipelineContext(video_id="test123")
        cache.set("metadata", ctx, {"title": "Test"})
        cache.invalidate("metadata", ctx)
        assert cache.get("metadata", ctx) is None

    def test_stats(self):
        cache = CacheManager()
        ctx = PipelineContext(video_id="test123")
        cache.set("meta", ctx, {"v": 1})
        cache.get("meta", ctx)
        cache.get("missing", ctx)
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1


# ---------------------------------------------------------------------------
# Pipeline Metrics
# ---------------------------------------------------------------------------


class TestPipelineMetrics:
    def test_record_pipeline(self):
        m = PipelineMetrics()
        m.record_pipeline_complete(10.5, True)
        m.record_pipeline_complete(20.3, False)
        report = m.get_report()
        assert report["pipelines"]["total"] == 2
        assert report["pipelines"]["success"] == 1
        assert report["pipelines"]["failed"] == 1

    def test_record_stage(self):
        m = PipelineMetrics()
        m.record_stage_complete("metadata", 2.5)
        m.record_stage_complete("transcript", 5.1)
        m.record_retry("metadata")
        report = m.get_report()
        assert "metadata" in report["stages"]["avg_durations"]
        assert report["stages"]["retries"]["metadata"] == 1

    def test_cache_metrics(self):
        m = PipelineMetrics()
        m.record_cache_hit()
        m.record_cache_hit()
        m.record_cache_miss()
        report = m.get_report()
        assert report["cache"]["hits"] == 2
        assert report["cache"]["misses"] == 1

    def test_llm_metrics(self):
        m = PipelineMetrics()
        m.record_llm_call(100)
        m.record_llm_call(200)
        report = m.get_report()
        assert report["llm"]["calls"] == 2
        assert report["llm"]["tokens"] == 300


# ---------------------------------------------------------------------------
# Pipeline Context
# ---------------------------------------------------------------------------


class TestPipelineContext:
    def test_store_and_get(self):
        ctx = PipelineContext(video_id="test123")
        ctx.store_stage_output("metadata", {"title": "Test Video"})
        assert ctx.get_stage_input("metadata")["title"] == "Test Video"

    def test_elapsed(self):
        ctx = PipelineContext()
        assert ctx.elapsed() <= 0.1
        old = ctx.started_at
        ctx.started_at = __import__("time").time() - 1.0
        assert ctx.elapsed() >= 0.9

    def test_get_dependency_output(self):
        ctx = PipelineContext()
        ctx.metadata = {"views": 1000}
        result = ctx.get_dependency_output("metadata")
        assert result["views"] == 1000


# ---------------------------------------------------------------------------
# Progress Emitter
# ---------------------------------------------------------------------------


class TestProgressEmitter:
    @pytest.mark.asyncio
    async def test_emit_events(self):
        bus = EventBus()
        emitter = ProgressEmitter(bus, "test123")
        emitter.set_total_stages(3)
        received = []

        async def handler(event: PipelineEvent):
            received.append(event.type)

        bus.subscribe_all(handler)
        await emitter.emit_pipeline_started()
        await emitter.emit_stage_started("metadata")
        await emitter.emit_stage_completed("metadata")
        assert PipelineEventType.PIPELINE_STARTED in received
        assert PipelineEventType.STAGE_STARTED in received
        assert PipelineEventType.STAGE_COMPLETED in received


# ---------------------------------------------------------------------------
# Pipeline Orchestrator (Integration)
# ---------------------------------------------------------------------------


class TestPipelineOrchestrator:
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()

        orchestrator = PipelineOrchestrator(project_manager=pm)

        from orchestrator.stages import MetadataStage
        orchestrator.register_stage(MetadataStage())

        assert orchestrator.registry.count >= 1
        assert orchestrator.registry.get("metadata") is not None

    @pytest.mark.asyncio
    async def test_create_and_run_pipeline(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        orchestrator = PipelineOrchestrator(project_manager=pm)

        from orchestrator.stages import MetadataStage, TranscriptStage, AnalysisStage
        orchestrator.register_stage(MetadataStage())
        orchestrator.register_stage(TranscriptStage())
        orchestrator.register_stage(AnalysisStage())

        result = await orchestrator.run_pipeline(project.project_id, video_id="test123")
        assert result["status"] == "started"
        assert result["total_stages"] >= 1

    @pytest.mark.asyncio
    async def test_pipeline_progress(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        orchestrator = PipelineOrchestrator(project_manager=pm)
        from orchestrator.stages import MetadataStage
        orchestrator.register_stage(MetadataStage())

        await orchestrator.run_pipeline(project.project_id, video_id="test123")
        progress = orchestrator.get_progress(project.project_id)
        assert progress is not None
        assert "state" in progress
        assert "progress_pct" in progress

    @pytest.mark.asyncio
    async def test_pause_resume_cancel(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        orchestrator = PipelineOrchestrator(project_manager=pm)
        from orchestrator.stages import MetadataStage
        orchestrator.register_stage(MetadataStage())

        controller = await orchestrator.create_pipeline(project.project_id, video_id="test123")
        assert controller is not None

        paused = await orchestrator.pause_pipeline(project.project_id)
        assert paused

        resumed = await orchestrator.resume_pipeline(project.project_id)
        assert resumed

        cancelled = await orchestrator.cancel_pipeline(project.project_id)
        assert cancelled

    def test_metrics_report(self):
        orchestrator = PipelineOrchestrator()
        report = orchestrator.get_metrics_report()
        assert "pipelines" in report
        assert "stages" in report
        assert "cache" in report

    def test_cache_stats(self):
        orchestrator = PipelineOrchestrator()
        stats = orchestrator.get_cache_stats()
        assert "hits" in stats
        assert "misses" in stats

    def test_empty_state(self):
        orchestrator = PipelineOrchestrator()
        assert orchestrator.active_pipelines == []
        assert orchestrator.get_progress("nonexistent") is None
        assert orchestrator.get_stage_info("nonexistent", "metadata") is None
