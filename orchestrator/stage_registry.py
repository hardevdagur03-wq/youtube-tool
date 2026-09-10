"""Stage Registry — registers and resolves pipeline stage executors.

No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from orchestrator.stage_executor import StageExecutor

logger = logging.getLogger(__name__)


class StageRegistry:
    """Registry of all available pipeline stage executors."""

    def __init__(self) -> None:
        self._stages: dict[str, StageExecutor] = {}

    def register(self, executor: StageExecutor) -> None:
        name = executor.name
        if name in self._stages:
            logger.warning("Overwriting existing stage: %s", name)
        self._stages[name] = executor
        logger.debug("Registered stage: %s", name)

    def get(self, name: str) -> StageExecutor | None:
        return self._stages.get(name)

    @property
    def all(self) -> dict[str, StageExecutor]:
        return dict(self._stages)

    @property
    def names(self) -> list[str]:
        return list(self._stages.keys())

    @property
    def count(self) -> int:
        return len(self._stages)

    def get_dependency_map(self) -> dict[str, list[str]]:
        return {
            name: list(executor.dependencies)
            for name, executor in self._stages.items()
        }

    def validate_all(self) -> list[str]:
        errors = []
        for name, executor in self._stages.items():
            for dep in executor.dependencies:
                if dep not in self._stages:
                    errors.append(f"Stage '{name}' depends on unknown stage '{dep}'")
        return errors
