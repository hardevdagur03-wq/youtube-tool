"""Stage Executor — generic interface for all pipeline stages.

Every stage exposes the same interface.
No existing module code is modified — existing modules are called via wrappers.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from orchestrator.pipeline_context import PipelineContext


@dataclass
class StageResult:
    """Result from a single stage execution."""
    success: bool
    stage: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    retry_count: int = 0
    cache_hit: bool = False
    artifacts: dict[str, str] = field(default_factory=dict)


class StageExecutor(ABC):
    """Abstract base class for all pipeline stage executors.

    Each concrete stage wraps an existing module without modifying it.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique stage name."""

    @property
    def dependencies(self) -> list[str]:
        """Stage names that must complete before this stage."""
        return []

    @property
    def is_cacheable(self) -> bool:
        """Whether this stage's output can be cached."""
        return True

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        """Validate inputs. Return list of error messages (empty = valid)."""
        return []

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> StageResult:
        """Execute the stage and return results."""
