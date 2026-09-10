"""Pipeline Orchestrator — top-level coordinator for pipeline execution.

Manages multiple pipeline controllers, event bus, and metrics.
No existing code is modified.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from orchestrator.pipeline_controller import PipelineController
from orchestrator.pipeline_events import EventBus, PipelineEvent, PipelineEventType
from orchestrator.pipeline_metrics import PipelineMetrics
from orchestrator.stage_registry import StageRegistry
from orchestrator.retry_manager import RetryManager, RetryPolicy
from orchestrator.error_handler import ErrorHandler
from orchestrator.cache_manager import CacheManager
from orchestrator.dependency_resolver import DependencyResolver
from projects.project_manager import ProjectManager

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Top-level orchestrator for all pipeline execution.

    Manages:
    - Multiple concurrent pipeline controllers
    - Global event bus
    - Metrics collection
    - Stage registration
    - Cache management
    """

    def __init__(self, project_manager: ProjectManager | None = None) -> None:
        self._pm = project_manager or ProjectManager()
        self._bus = EventBus()
        self._metrics = PipelineMetrics()
        self._registry = StageRegistry()
        self._retry = RetryManager(RetryPolicy(
            max_retries=3, base_delay=2.0, max_delay=60.0,
        ))
        self._cache = CacheManager()
        self._resolver = DependencyResolver()
        self._controllers: dict[str, PipelineController] = {}
        self._error_handler = ErrorHandler()

        self._setup_default_subscribers()

    def _setup_default_subscribers(self) -> None:
        """Log all events by default."""
        async def log_event(event: PipelineEvent) -> None:
            if event.type in (
                PipelineEventType.STAGE_STARTED,
                PipelineEventType.STAGE_COMPLETED,
                PipelineEventType.STAGE_FAILED,
                PipelineEventType.PIPELINE_STARTED,
                PipelineEventType.PIPELINE_COMPLETED,
                PipelineEventType.PIPELINE_FAILED,
            ):
                logger.info(
                    "[%s] %s: %s", event.project_id[:8],
                    event.type.value, event.message,
                )

        self._bus.subscribe_all(log_event)

    @property
    def event_bus(self) -> EventBus:
        return self._bus

    @property
    def metrics(self) -> PipelineMetrics:
        return self._metrics

    @property
    def registry(self) -> StageRegistry:
        return self._registry

    @property
    def cache(self) -> CacheManager:
        return self._cache

    @property
    def project_manager(self) -> ProjectManager:
        return self._pm

    def register_stage(self, executor: Any) -> None:
        self._registry.register(executor)

    async def create_pipeline(
        self,
        project_id: str,
        video_id: str = "",
        url: str = "",
    ) -> PipelineController:
        controller = PipelineController(
            project_id=project_id,
            event_bus=self._bus,
            stage_registry=self._registry,
            retry_manager=self._retry,
            cache_manager=self._cache,
            metrics=self._metrics,
            project_manager=self._pm,
            dependency_resolver=self._resolver,
        )
        self._controllers[project_id] = controller
        await controller.initialize(video_id=video_id, url=url)
        return controller

    async def run_pipeline(
        self,
        project_id: str,
        video_id: str = "",
        url: str = "",
    ) -> dict[str, Any]:
        controller = await self.create_pipeline(project_id, video_id, url)

        async def _run() -> None:
            await controller.execute_pipeline()

        task = asyncio.create_task(_run())
        return {
            "project_id": project_id,
            "status": "started",
            "total_stages": self._registry.count,
        }

    def get_controller(self, project_id: str) -> PipelineController | None:
        return self._controllers.get(project_id)

    async def pause_pipeline(self, project_id: str) -> bool:
        controller = self.get_controller(project_id)
        if controller is None:
            return False
        await controller.pause()
        return True

    async def resume_pipeline(self, project_id: str) -> bool:
        controller = self.get_controller(project_id)
        if controller is None:
            return False
        await controller.resume()
        return True

    async def cancel_pipeline(self, project_id: str) -> bool:
        controller = self.get_controller(project_id)
        if controller is None:
            return False
        await controller.cancel()
        return True

    def get_progress(self, project_id: str) -> dict[str, Any] | None:
        controller = self.get_controller(project_id)
        if controller is None:
            return None
        return controller.get_progress()

    def get_stage_info(self, project_id: str, stage: str) -> dict[str, Any] | None:
        controller = self.get_controller(project_id)
        if controller is None:
            return None
        info = controller.get_stage_info(stage)
        if info is None:
            return None
        return info.to_dict()

    def get_history(self, project_id: str, limit: int = 50) -> list[dict[str, Any]]:
        events = self._bus.get_history_for(project_id, limit=limit)
        return [
            {
                "type": e.type.value,
                "stage": e.stage,
                "message": e.message,
                "timestamp": e.timestamp,
                "data": e.data,
            }
            for e in events
        ]

    def get_metrics_report(self) -> dict[str, Any]:
        return self._metrics.get_report()

    def get_cache_stats(self) -> dict[str, Any]:
        return self._cache.stats

    def clear_cache(self) -> None:
        self._cache.clear_all()

    @property
    def active_pipelines(self) -> list[str]:
        return [
            pid for pid, ctrl in self._controllers.items()
            if ctrl.state.value in ("running", "paused", "ready")
        ]
