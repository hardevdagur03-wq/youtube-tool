"""Pipeline Controller — manages pipeline lifecycle.

Loads project, initializes runtime, executes stages via the orchestrator.
No existing code is modified.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from orchestrator.pipeline_state import PipelineState, StageState, StageInfo
from orchestrator.pipeline_context import PipelineContext
from orchestrator.pipeline_events import EventBus, PipelineEvent, PipelineEventType
from orchestrator.execution_graph import ExecutionGraph
from orchestrator.dependency_resolver import DependencyResolver
from orchestrator.stage_registry import StageRegistry
from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.retry_manager import RetryManager, RetryPolicy
from orchestrator.error_handler import ErrorHandler, PipelineError as PipeError
from orchestrator.progress_emitter import ProgressEmitter
from orchestrator.cache_manager import CacheManager
from orchestrator.pipeline_metrics import PipelineMetrics
from projects.project_manager import ProjectManager

logger = logging.getLogger(__name__)


class PipelineController:
    """Controls the lifecycle of a single pipeline run."""

    def __init__(
        self,
        project_id: str,
        event_bus: EventBus,
        stage_registry: StageRegistry,
        retry_manager: RetryManager,
        cache_manager: CacheManager,
        metrics: PipelineMetrics,
        project_manager: ProjectManager,
        dependency_resolver: DependencyResolver | None = None,
    ) -> None:
        self._project_id = project_id
        self._bus = event_bus
        self._registry = stage_registry
        self._retry = retry_manager
        self._cache = cache_manager
        self._metrics = metrics
        self._pm = project_manager
        self._resolver = dependency_resolver or DependencyResolver()

        self._state = PipelineState.NOT_STARTED
        self._ctx: PipelineContext | None = None
        self._stage_infos: dict[str, StageInfo] = {}
        self._emitter: ProgressEmitter | None = None
        self._graph: ExecutionGraph | None = None
        self._cancel_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._execution_task: asyncio.Task | None = None

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def context(self) -> PipelineContext | None:
        return self._ctx

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    async def initialize(self, video_id: str = "", url: str = "") -> PipelineContext:
        self._state = PipelineState.READY
        project = self._pm.get_project(self._project_id)

        if project is None:
            project = self._pm.create_project(url=url, video_id=video_id)

        self._ctx = PipelineContext(
            project_id=self._project_id,
            video_id=project.video_id or video_id,
            url=project.url or url,
            project=project,
            project_manager=self._pm,
            started_at=time.time(),
        )
        self._emitter = ProgressEmitter(self._bus, self._project_id)

        stages = self._registry.names
        self._emitter.set_total_stages(len(stages))
        self._graph = self._resolver.build_graph(stages)

        for stage_name in self._graph.topological_sort():
            self._stage_infos[stage_name] = StageInfo(
                name=stage_name,
                dependencies=self._graph.get_upstream(stage_name),
            )

        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.PIPELINE_STARTED,
            project_id=self._project_id,
            message=f"Pipeline initialized with {len(stages)} stages",
            data={"stages": stages, "execution_order": self._graph.topological_sort()},
        ))
        return self._ctx

    async def execute_pipeline(self) -> PipelineContext:
        if self._ctx is None:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")

        self._state = PipelineState.RUNNING
        await self._emitter.emit_pipeline_started()
        self._pm.stage_started(self._project_id, "pipeline")

        execution_order = self._graph.topological_sort()

        for stage_name in execution_order:
            if self._cancel_event.is_set():
                await self._handle_cancellation()
                return self._ctx

            await self._pause_event.wait()

            await self._execute_single_stage(stage_name)

            if self._cancel_event.is_set():
                await self._handle_cancellation()
                return self._ctx

        all_success = all(
            info.state == StageState.SUCCESS
            for info in self._stage_infos.values()
        )

        if all_success:
            self._state = PipelineState.COMPLETED
            await self._emitter.emit_pipeline_completed()
            self._pm.complete_project(self._project_id)
            self._metrics.record_pipeline_complete(self._ctx.elapsed(), True)
        else:
            self._state = PipelineState.FAILED
            await self._emitter.emit_pipeline_failed("One or more stages failed")
            self._metrics.record_pipeline_complete(self._ctx.elapsed(), False)

        return self._ctx

    async def _execute_single_stage(self, stage_name: str) -> None:
        executor = self._registry.get(stage_name)
        if executor is None:
            logger.error("No executor registered for stage: %s", stage_name)
            return

        info = self._stage_infos[stage_name]
        info.mark_running()
        await self._emitter.emit_stage_started(stage_name)
        self._pm.stage_started(self._project_id, stage_name)

        # Check cache
        cache_hit = False
        if executor.is_cacheable:
            cached = self._cache.get(stage_name, self._ctx)
            if cached is not None:
                info.cache_hit = True
                cache_hit = True
                info.output = cached
                info.mark_success()
                self._cache.record_hit()
                self._metrics.record_cache_hit()
                self._ctx.cache_hits += 1
                self._ctx.store_stage_output(stage_name, cached)
                await self._emitter.emit_stage_completed(stage_name, info)
                self._pm.stage_completed(self._project_id, stage_name)
                return

        self._cache.record_miss()
        self._metrics.record_cache_miss()
        self._ctx.cache_misses += 1

        # Validate input
        validation_errors = await executor.validate_input(self._ctx)
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            info.mark_failed(error_msg)
            await self._emitter.emit_stage_failed(stage_name, error_msg)
            self._pm.stage_failed(self._project_id, stage_name, error_msg)
            return

        # Execute with retry
        start = time.time()
        success, result_data, error, retries = await self._retry.execute_with_retry(
            stage_name, self._execute_stage_with_context, executor,
        )

        duration = time.time() - start
        self._metrics.record_stage_complete(stage_name, duration)
        self._ctx.total_retries += retries

        if success and result_data is not None:
            info.output = result_data.data if isinstance(result_data, StageResult) else {}
            info.mark_success()
            info.retry_count = retries
            self._ctx.store_stage_output(stage_name, info.output)

            if executor.is_cacheable:
                self._cache.set(stage_name, self._ctx, info.output)

            await self._emitter.emit_stage_completed(stage_name, info)
            await self._emitter.emit_checkpoint(stage_name)
            self._pm.stage_completed(self._project_id, stage_name)

            self._pm.update_stage_progress(
                self._project_id, stage_name, 100.0,
                f"Completed in {duration:.1f}s",
            )
        else:
            info.mark_failed(error)
            await self._emitter.emit_stage_failed(stage_name, error)
            pe = ErrorHandler.classify(Exception(error), stage_name)
            ErrorHandler.log_error(pe)
            self._metrics.record_error(pe.error_type)
            self._pm.stage_failed(self._project_id, stage_name, error)

    async def _execute_stage_with_context(self, executor: StageExecutor) -> StageResult:
        return await executor.execute(self._ctx)

    async def _handle_cancellation(self) -> None:
        self._state = PipelineState.CANCELLED
        await self._emitter.emit_pipeline_completed({"cancelled": True})
        self._pm.cancel_project(self._project_id)

    async def pause(self) -> None:
        if self._state == PipelineState.RUNNING:
            self._state = PipelineState.PAUSED
            self._pause_event.clear()
            self._pm.pause_project(self._project_id)
            await self._bus.emit(PipelineEvent(
                type=PipelineEventType.PIPELINE_PAUSED,
                project_id=self._project_id,
            ))

    async def resume(self) -> None:
        if self._state == PipelineState.PAUSED:
            self._state = PipelineState.RUNNING
            self._pause_event.set()
            self._pm.resume_project(self._project_id)
            await self._bus.emit(PipelineEvent(
                type=PipelineEventType.PIPELINE_RESUMED,
                project_id=self._project_id,
            ))

    async def cancel(self) -> None:
        self._cancel_event.set()
        self._pause_event.set()
        if self._execution_task and not self._execution_task.done():
            self._execution_task.cancel()

    def get_stage_info(self, stage: str) -> StageInfo | None:
        return self._stage_infos.get(stage)

    def get_progress(self) -> dict[str, Any]:
        if not self._ctx:
            return {"state": self._state.value, "progress_pct": 0.0}
        completed = sum(1 for s in self._stage_infos.values() if s.is_completed)
        total = len(self._stage_infos)
        pct = round((completed / max(total, 1)) * 100, 1)
        return {
            "state": self._state.value,
            "progress_pct": pct,
            "completed_stages": completed,
            "total_stages": total,
            "elapsed_seconds": round(self._ctx.elapsed(), 1),
            "stages": {name: info.to_dict() for name, info in self._stage_infos.items()},
        }
