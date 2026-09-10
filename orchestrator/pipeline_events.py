"""Event Bus — internal pub/sub communication between components.

No module communicates directly.
All communication flows through events.
No existing code is modified.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class PipelineEventType(enum.Enum):
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"
    PIPELINE_CANCELLED = "pipeline_cancelled"
    PIPELINE_PAUSED = "pipeline_paused"
    PIPELINE_RESUMED = "pipeline_resumed"

    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    STAGE_SKIPPED = "stage_skipped"
    STAGE_CANCELLED = "stage_cancelled"
    STAGE_RETRYING = "stage_retrying"

    PROGRESS_UPDATED = "progress_updated"
    CHECKPOINT_CREATED = "checkpoint_created"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    ARTIFACT_STORED = "artifact_stored"

    ERROR_OCCURRED = "error_occurred"
    WARNING_RAISED = "warning_raised"


@dataclass
class PipelineEvent:
    type: PipelineEventType
    project_id: str = ""
    stage: str = ""
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def elapsed(self) -> float:
        return time.time() - self.timestamp


EventHandler = Callable[["PipelineEvent"], Coroutine[Any, Any, None]]


class EventBus:
    """Async pub/sub event bus for internal pipeline communication."""

    def __init__(self) -> None:
        self._subscribers: dict[PipelineEventType, list[EventHandler]] = {}
        self._global_subscribers: list[EventHandler] = []
        self._history: list[PipelineEvent] = []
        self._max_history = 1000

    def subscribe(self, event_type: PipelineEventType, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._global_subscribers.append(handler)

    def unsubscribe(self, event_type: PipelineEventType, handler: EventHandler) -> None:
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: PipelineEvent) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        tasks = []
        for handler in self._global_subscribers:
            tasks.append(self._safe_dispatch(handler, event))

        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            tasks.append(self._safe_dispatch(handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_dispatch(self, handler: EventHandler, event: PipelineEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.error("Event handler %s failed: %s", handler.__name__, exc)

    def get_history(self, limit: int = 50) -> list[PipelineEvent]:
        return self._history[-limit:]

    def get_history_for(self, project_id: str, limit: int = 50) -> list[PipelineEvent]:
        return [e for e in self._history if e.project_id == project_id][-limit:]

    def clear_history(self) -> None:
        self._history.clear()
