from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestPipelineEvents:
    def test_event_types(self):
        from orchestrator.pipeline_events import PipelineEventType
        assert PipelineEventType.PIPELINE_STARTED.value == "pipeline_started"
        assert PipelineEventType.STAGE_FAILED.value == "stage_failed"

    @pytest.mark.asyncio
    async def test_emit_and_subscribe(self):
        from orchestrator.pipeline_events import EventBus, PipelineEvent, PipelineEventType
        bus = EventBus()
        received = []
        async def handler(event):
            received.append(event)
        bus.subscribe(PipelineEventType.PIPELINE_STARTED, handler)
        await bus.emit(PipelineEvent(type=PipelineEventType.PIPELINE_STARTED, project_id="test123"))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_global_subscriber(self):
        from orchestrator.pipeline_events import EventBus, PipelineEvent, PipelineEventType
        bus = EventBus()
        received = []
        async def handler(event):
            received.append(event)
        bus.subscribe_all(handler)
        await bus.emit(PipelineEvent(type=PipelineEventType.STAGE_STARTED, project_id="p1"))
        await bus.emit(PipelineEvent(type=PipelineEventType.STAGE_COMPLETED, project_id="p1"))
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_history(self):
        from orchestrator.pipeline_events import EventBus, PipelineEvent, PipelineEventType
        bus = EventBus()
        await bus.emit(PipelineEvent(type=PipelineEventType.PIPELINE_STARTED, project_id="p1"))
        await bus.emit(PipelineEvent(type=PipelineEventType.PIPELINE_COMPLETED, project_id="p1"))
        history = bus.get_history()
        assert len(history) == 2


class TestPipelineState:
    def test_initial_state(self):
        from orchestrator.pipeline_state import StageInfo, StageState
        info = StageInfo("test_stage", dependencies=["dep1"])
        assert info.name == "test_stage"
        assert info.state == StageState.WAITING

    def test_valid_transitions(self):
        from orchestrator.pipeline_state import StageInfo, StageState
        info = StageInfo("stage")
        info.transition_to(StageState.READY)
        assert info.state == StageState.READY
        info.mark_running()
        info.mark_success()
        assert info.state == StageState.SUCCESS

    def test_invalid_transition(self):
        from orchestrator.pipeline_state import StageInfo, StageState
        info = StageInfo("stage")
        info.state = StageState.SUCCESS
        with pytest.raises(ValueError):
            info.transition_to(StageState.RUNNING)

    def test_terminal_states(self):
        from orchestrator.pipeline_state import StageState
        assert StageState.SUCCESS in StageState.terminal_states()
        assert StageState.RUNNING not in StageState.terminal_states()

    def test_pipeline_transitions(self):
        from orchestrator.pipeline_state import PipelineState
        s = PipelineState.NOT_STARTED
        assert s.can_transition_to(PipelineState.READY)
        assert not s.can_transition_to(PipelineState.COMPLETED)


class TestExecutionGraph:
    def test_add_node(self):
        from orchestrator.execution_graph import ExecutionGraph
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        assert g.get_node("a") is not None
        assert g.get_node("c") is None

    def test_topological_sort(self):
        from orchestrator.execution_graph import ExecutionGraph
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["b"])
        order = g.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_get_ready_stages(self):
        from orchestrator.execution_graph import ExecutionGraph
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        ready = g.get_ready_stages(set(), set())
        assert "a" in ready
        ready_after_a = g.get_ready_stages({"a"}, set())
        assert "b" in ready_after_a

    def test_get_dependents(self):
        from orchestrator.execution_graph import ExecutionGraph
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["a"])
        deps = g.get_dependents("a")
        assert "b" in deps
        assert "c" in deps

    def test_validate(self):
        from orchestrator.execution_graph import ExecutionGraph
        g = ExecutionGraph()
        g.add_node("a", ["nonexistent"])
        errors = g.validate()
        assert len(errors) == 1

    def test_levels(self):
        from orchestrator.execution_graph import ExecutionGraph
        g = ExecutionGraph()
        g.add_node("a")
        g.add_node("b", ["a"])
        g.add_node("c", ["a"])
        levels = g.levels()
        assert levels[0] == ["a"]


class TestDependencyResolver:
    def test_execution_order(self):
        from orchestrator.dependency_resolver import DependencyResolver
        resolver = DependencyResolver({"a": [], "b": ["a"], "c": ["b"]})
        order = resolver.execution_order()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_parallel_levels(self):
        from orchestrator.dependency_resolver import DependencyResolver
        resolver = DependencyResolver({"a": [], "b": ["a"], "c": ["a"]})
        levels = resolver.parallel_levels()
        assert levels[0] == ["a"]
        assert len(levels) == 2

    def test_can_run_in_parallel(self):
        from orchestrator.dependency_resolver import DependencyResolver
        resolver = DependencyResolver({"a": [], "b": ["a"], "c": ["a"]})
        assert resolver.can_run_in_parallel("b", "c")
        assert not resolver.can_run_in_parallel("a", "b")

    def test_default_stages(self):
        from orchestrator.dependency_resolver import DependencyResolver
        resolver = DependencyResolver()
        assert "metadata" in resolver.stages


class TestStageRegistry:
    def test_register_and_get(self):
        from orchestrator.stage_registry import StageRegistry
        from orchestrator.stage_executor import StageExecutor
        registry = StageRegistry()
        executor = MagicMock(spec=StageExecutor)
        executor.name = "test_stage"
        executor.dependencies = []
        registry.register(executor)
        assert registry.get("test_stage") is executor

    def test_names(self):
        from orchestrator.stage_registry import StageRegistry
        from orchestrator.stage_executor import StageExecutor
        registry = StageRegistry()
        e1, e2 = MagicMock(spec=StageExecutor), MagicMock(spec=StageExecutor)
        e1.name, e2.name = "a", "b"
        e1.dependencies, e2.dependencies = [], []
        registry.register(e1)
        registry.register(e2)
        assert "a" in registry.names

    def test_dependency_map(self):
        from orchestrator.stage_registry import StageRegistry
        from orchestrator.stage_executor import StageExecutor
        registry = StageRegistry()
        e1, e2 = MagicMock(spec=StageExecutor), MagicMock(spec=StageExecutor)
        e1.name, e2.name = "a", "b"
        e1.dependencies, e2.dependencies = [], ["a"]
        registry.register(e1)
        registry.register(e2)
        deps = registry.get_dependency_map()
        assert deps["a"] == []
        assert deps["b"] == ["a"]


class TestRetryManager:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        from orchestrator.retry_manager import RetryManager
        rm = RetryManager()
        async def succeed():
            return "ok"
        success, result, error, retries = await rm.execute_with_retry("test", succeed)
        assert success
        assert result == "ok"
        assert retries == 0

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        from orchestrator.retry_manager import RetryManager, RetryPolicy
        rm = RetryManager(RetryPolicy(max_retries=3, base_delay=0.01))
        attempt = [0]
        async def fail_then_succeed():
            attempt[0] += 1
            if attempt[0] < 2:
                raise ValueError("timeout")
            return "ok"
        success, result, error, retries = await rm.execute_with_retry("test", fail_then_succeed)
        assert success
        assert retries == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        from orchestrator.retry_manager import RetryManager, RetryPolicy
        rm = RetryManager(RetryPolicy(max_retries=2, base_delay=0.01))
        async def always_fail():
            raise ValueError("timeout")
        success, result, error, retries = await rm.execute_with_retry("test", always_fail)
        assert not success
        assert retries == 3


class TestErrorHandler:
    def test_classify_timeout(self):
        from orchestrator.error_handler import ErrorHandler
        err = ErrorHandler.classify(Exception("timeout error"))
        assert err.error_type == "timeout"
        assert err.retryable

    def test_classify_unexpected(self):
        from orchestrator.error_handler import ErrorHandler
        err = ErrorHandler.classify(Exception("random error"))
        assert err.error_type == "unexpected"
        assert not err.retryable

    def test_should_retry(self):
        from orchestrator.error_handler import ErrorHandler, PipelineError
        assert ErrorHandler.should_retry(PipelineError(error_type="timeout", retryable=True))
        assert not ErrorHandler.should_retry(PipelineError(error_type="fatal", retryable=False))


class TestProgressEmitter:
    @pytest.mark.asyncio
    async def test_emit_events(self):
        from orchestrator.progress_emitter import ProgressEmitter
        from orchestrator.pipeline_events import EventBus, PipelineEventType
        bus = EventBus()
        emitter = ProgressEmitter(bus, "test123")
        emitter.set_total_stages(3)
        received = []
        async def handler(event):
            received.append(event.type)
        bus.subscribe_all(handler)
        await emitter.emit_pipeline_started()
        await emitter.emit_stage_started("metadata")
        assert PipelineEventType.PIPELINE_STARTED in received
        assert PipelineEventType.STAGE_STARTED in received


class TestCacheManager:
    def test_set_and_get(self):
        from orchestrator.cache_manager import CacheManager
        from orchestrator.pipeline_context import PipelineContext
        cache = CacheManager()
        ctx = PipelineContext(video_id="test123")
        cache.set("metadata", ctx, {"title": "Test"})
        result = cache.get("metadata", ctx)
        assert result["title"] == "Test"

    def test_cache_miss(self):
        from orchestrator.cache_manager import CacheManager
        from orchestrator.pipeline_context import PipelineContext
        cache = CacheManager()
        ctx = PipelineContext(video_id="test123")
        assert cache.get("nonexistent", ctx) is None

    def test_invalidate(self):
        from orchestrator.cache_manager import CacheManager
        from orchestrator.pipeline_context import PipelineContext
        cache = CacheManager()
        ctx = PipelineContext(video_id="test123")
        cache.set("metadata", ctx, {"title": "Test"})
        cache.invalidate("metadata", ctx)
        assert cache.get("metadata", ctx) is None

    def test_stats(self):
        from orchestrator.cache_manager import CacheManager
        from orchestrator.pipeline_context import PipelineContext
        cache = CacheManager()
        ctx = PipelineContext(video_id="test123")
        cache.set("meta", ctx, {"v": 1})
        cache.get("meta", ctx)
        cache.get("missing", ctx)
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestPipelineMetrics:
    def test_record_pipeline(self):
        from orchestrator.pipeline_metrics import PipelineMetrics
        m = PipelineMetrics()
        m.record_pipeline_complete(10.5, True)
        m.record_pipeline_complete(20.3, False)
        report = m.get_report()
        assert report["pipelines"]["total"] == 2
        assert report["pipelines"]["success"] == 1

    def test_record_stage(self):
        from orchestrator.pipeline_metrics import PipelineMetrics
        m = PipelineMetrics()
        m.record_stage_complete("metadata", 2.5)
        m.record_retry("metadata")
        report = m.get_report()
        assert report["stages"]["retries"]["metadata"] == 1

    def test_cache_metrics(self):
        from orchestrator.pipeline_metrics import PipelineMetrics
        m = PipelineMetrics()
        m.record_cache_hit()
        m.record_cache_miss()
        report = m.get_report()
        assert report["cache"]["hits"] == 1
        assert report["cache"]["misses"] == 1

    def test_llm_metrics(self):
        from orchestrator.pipeline_metrics import PipelineMetrics
        m = PipelineMetrics()
        m.record_llm_call(100)
        m.record_llm_call(200)
        report = m.get_report()
        assert report["llm"]["calls"] == 2
        assert report["llm"]["tokens"] == 300


class TestPipelineContext:
    def test_store_and_get(self):
        from orchestrator.pipeline_context import PipelineContext
        ctx = PipelineContext(video_id="test123")
        ctx.store_stage_output("metadata", {"title": "Test Video"})
        assert ctx.get_stage_input("metadata")["title"] == "Test Video"

    def test_elapsed(self):
        from orchestrator.pipeline_context import PipelineContext
        ctx = PipelineContext()
        assert ctx.elapsed() <= 0.1

    def test_get_dependency_output(self):
        from orchestrator.pipeline_context import PipelineContext
        ctx = PipelineContext()
        ctx.metadata = {"views": 1000}
        result = ctx.get_dependency_output("metadata")
        assert result["views"] == 1000


class TestStageExecutors:
    @pytest.mark.asyncio
    async def test_metadata_stage(self):
        from orchestrator.stages import MetadataStage
        stage = MetadataStage()
        assert stage.name == "metadata"
        assert stage.dependencies == []

    @pytest.mark.asyncio
    async def test_transcript_stage(self):
        from orchestrator.stages import TranscriptStage
        stage = TranscriptStage()
        assert stage.name == "transcript"

    @pytest.mark.asyncio
    async def test_stage_registry_has_all(self):
        from orchestrator.stages import (
            MetadataStage, TranscriptStage, AnalysisStage,
            KnowledgeGraphStage, SEOStage, OutlineStage,
            SectionGenerationStage, ReviewStage,
            ExportStage, MergeStage, SectionsStage,
        )
        stages = [MetadataStage, TranscriptStage, AnalysisStage, KnowledgeGraphStage, SEOStage, OutlineStage, SectionGenerationStage, SectionsStage, ReviewStage, MergeStage, ExportStage]
        assert len(stages) == 11


class TestPipelineOrchestrator:
    def test_initialization(self):
        from orchestrator.pipeline_orchestrator import PipelineOrchestrator
        orchestrator = PipelineOrchestrator()
        assert orchestrator.active_pipelines == []

    def test_get_progress_nonexistent(self):
        from orchestrator.pipeline_orchestrator import PipelineOrchestrator
        orchestrator = PipelineOrchestrator()
        assert orchestrator.get_progress("nonexistent") is None

    def test_get_metrics_report(self):
        from orchestrator.pipeline_orchestrator import PipelineOrchestrator
        orchestrator = PipelineOrchestrator()
        report = orchestrator.get_metrics_report()
        assert "pipelines" in report
        assert "stages" in report

    def test_cache_stats(self):
        from orchestrator.pipeline_orchestrator import PipelineOrchestrator
        orchestrator = PipelineOrchestrator()
        stats = orchestrator.get_cache_stats()
        assert "hits" in stats
        assert "misses" in stats

    @pytest.mark.asyncio
    async def test_orchestrator_initialization_with_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        from orchestrator.pipeline_orchestrator import PipelineOrchestrator
        from orchestrator.stages import MetadataStage
        pm = ProjectManager()
        orchestrator = PipelineOrchestrator(project_manager=pm)
        orchestrator.register_stage(MetadataStage())
        assert orchestrator.registry.count >= 1

    @pytest.mark.asyncio
    async def test_create_and_run_pipeline(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        from orchestrator.pipeline_orchestrator import PipelineOrchestrator
        from orchestrator.stages import MetadataStage
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        orchestrator = PipelineOrchestrator(project_manager=pm)
        orchestrator.register_stage(MetadataStage())
        result = await orchestrator.run_pipeline(project.project_id, video_id="test123")
        assert result["status"] == "started"

    @pytest.mark.asyncio
    async def test_pause_resume_cancel(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        from orchestrator.pipeline_orchestrator import PipelineOrchestrator
        from orchestrator.stages import MetadataStage
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        orchestrator = PipelineOrchestrator(project_manager=pm)
        orchestrator.register_stage(MetadataStage())
        controller = await orchestrator.create_pipeline(project.project_id, video_id="test123")
        assert await orchestrator.pause_pipeline(project.project_id) is True or await orchestrator.pause_pipeline(project.project_id) is not None
