"""Pipeline State Machine — manages execution state for pipelines and stages.

All state transitions are validated.
No existing code is modified.
"""

from __future__ import annotations

import enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class StageState(enum.Enum):
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

    @classmethod
    def terminal_states(cls) -> set["StageState"]:
        return {cls.SUCCESS, cls.FAILED, cls.SKIPPED, cls.CANCELLED}

    @classmethod
    def active_states(cls) -> set["StageState"]:
        return {cls.READY, cls.RUNNING}

    def can_transition_to(self, target: "StageState") -> bool:
        VALID_TRANSITIONS = {
            StageState.WAITING: {StageState.READY, StageState.SKIPPED, StageState.CANCELLED},
            StageState.READY: {StageState.RUNNING, StageState.SKIPPED, StageState.CANCELLED},
            StageState.RUNNING: {StageState.SUCCESS, StageState.FAILED, StageState.CANCELLED},
            StageState.SUCCESS: set(),
            StageState.FAILED: {StageState.READY},
            StageState.SKIPPED: set(),
            StageState.CANCELLED: set(),
        }
        return target in VALID_TRANSITIONS.get(self, set())


class PipelineState(enum.Enum):
    NOT_STARTED = "not_started"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @classmethod
    def terminal_states(cls) -> set["PipelineState"]:
        return {cls.COMPLETED, cls.FAILED, cls.CANCELLED}

    def can_transition_to(self, target: "PipelineState") -> bool:
        VALID_TRANSITIONS = {
            PipelineState.NOT_STARTED: {PipelineState.READY, PipelineState.CANCELLED},
            PipelineState.READY: {PipelineState.RUNNING, PipelineState.CANCELLED},
            PipelineState.RUNNING: {PipelineState.COMPLETED, PipelineState.FAILED,
                                    PipelineState.PAUSED, PipelineState.CANCELLED},
            PipelineState.PAUSED: {PipelineState.RUNNING, PipelineState.CANCELLED},
            PipelineState.FAILED: {PipelineState.READY},
            PipelineState.COMPLETED: set(),
            PipelineState.CANCELLED: set(),
        }
        return target in VALID_TRANSITIONS.get(self, set())


class StageInfo:
    """Runtime information for a single pipeline stage."""

    def __init__(self, name: str, dependencies: list[str] | None = None) -> None:
        self.name = name
        self.state = StageState.WAITING
        self.dependencies = dependencies or []
        self.started_at: float = 0.0
        self.finished_at: float = 0.0
        self.duration: float = 0.0
        self.retry_count: int = 0
        self.error: str = ""
        self.warnings: list[str] = []
        self.output: dict[str, Any] = {}
        self.cache_hit: bool = False

    @property
    def is_terminal(self) -> bool:
        return self.state in StageState.terminal_states()

    @property
    def is_completed(self) -> bool:
        return self.state == StageState.SUCCESS

    def transition_to(self, target: StageState) -> None:
        if not self.state.can_transition_to(target):
            raise ValueError(f"Invalid stage transition: {self.state.value} -> {target.value}")
        self.state = target

    def mark_running(self) -> None:
        self.started_at = __import__("time").time()
        self.transition_to(StageState.RUNNING)

    def mark_success(self) -> None:
        self.finished_at = __import__("time").time()
        self.duration = self.finished_at - self.started_at
        self.transition_to(StageState.SUCCESS)

    def mark_failed(self, error: str = "") -> None:
        self.finished_at = __import__("time").time()
        self.duration = self.finished_at - self.started_at
        self.error = error
        self.transition_to(StageState.FAILED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "dependencies": self.dependencies,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration": round(self.duration, 3),
            "retry_count": self.retry_count,
            "error": self.error,
            "warnings": self.warnings,
            "cache_hit": self.cache_hit,
        }
