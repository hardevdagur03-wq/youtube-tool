"""Pipeline Context — shared state across pipeline stages.

All stage inputs, outputs, and configuration flow through this context.
No existing code is modified.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from projects.project_manager import ProjectManager
from projects.project_models import Project


@dataclass
class PipelineContext:
    """Shared context for pipeline execution.

    All stages read inputs from and write outputs to this context.
    """

    project_id: str = ""
    video_id: str = ""
    url: str = ""
    project: Project | None = None
    project_manager: ProjectManager | None = None

    started_at: float = 0.0
    stage_timings: dict[str, float] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)
    transcript: dict[str, Any] = field(default_factory=dict)
    analysis: dict[str, Any] = field(default_factory=dict)
    seo: dict[str, Any] = field(default_factory=dict)
    outline: dict[str, Any] = field(default_factory=dict)
    sections: list[dict[str, Any]] = field(default_factory=list)
    merged_blog: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)
    export: dict[str, Any] = field(default_factory=dict)

    settings: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    total_retries: int = 0

    def elapsed(self) -> float:
        if self.started_at == 0:
            return 0.0
        return time.time() - self.started_at

    def store_stage_output(self, stage: str, data: dict[str, Any]) -> None:
        setattr(self, stage, data)

    def get_stage_input(self, stage: str) -> dict[str, Any]:
        return getattr(self, stage, {})

    def get_dependency_output(self, dependency: str) -> dict[str, Any]:
        return getattr(self, dependency, {})
