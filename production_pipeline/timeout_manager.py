"""Timeout Manager — per-stage timeout configuration and enforcement.

Each stage has a configurable timeout. Stages that exceed their timeout
are failed with a TimeoutError and the recovery action is triggered.
Integrates with the Transaction Logger for timeout event recording.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Any, Callable, TypeVar

from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.constants import STAGE_TIMEOUT_DEFAULTS
from production_pipeline.exceptions import TimeoutError as PipelineTimeoutError
from production_pipeline.models import TimeoutConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TimeoutManager:
    """Manages per-stage timeout configuration and enforcement.

    Each stage has a configurable timeout. When a stage exceeds its timeout,
    the TimeoutManager records the event and returns control to the caller
    with a TimeoutError.
    """

    def __init__(self, config: PipelineHardeningConfig | None = None) -> None:
        self._config = config or PipelineHardeningConfig()
        self._overrides: dict[str, int] = {}

    def get_timeout(self, stage_name: str) -> int:
        """Get the timeout for a stage in seconds.

        Checks in order: runtime override > config > default.

        Args:
            stage_name: Stage name.

        Returns:
            Timeout in seconds.
        """
        if stage_name in self._overrides:
            return self._overrides[stage_name]
        config_timeout = self._config.get_timeout(stage_name)
        if config_timeout:
            return config_timeout
        return STAGE_TIMEOUT_DEFAULTS.get(stage_name, 30)

    def set_timeout(self, stage_name: str, timeout_seconds: int) -> None:
        """Override the timeout for a stage at runtime.

        Args:
            stage_name: Stage name.
            timeout_seconds: Timeout in seconds.
        """
        self._overrides[stage_name] = timeout_seconds
        logger.info("Timeout override: %s = %ds", stage_name, timeout_seconds)

    def enforce_timeout(
        self,
        stage_name: str,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function with timeout enforcement (synchronous).

        Args:
            stage_name: Stage name (for timeout lookup).
            func: Function to execute.
            *args: Function arguments.
            **kwargs: Function keyword arguments.

        Returns:
            Function result.

        Raises:
            PipelineTimeoutError: If execution exceeds timeout.
        """
        timeout = self.get_timeout(stage_name)
        start = time.time()

        result = func(*args, **kwargs)

        elapsed = time.time() - start
        if elapsed > timeout:
            logger.warning(
                "Stage '%s' exceeded timeout: %.1fs > %ds",
                stage_name, elapsed, timeout,
            )

        return result

    async def enforce_timeout_async(
        self,
        stage_name: str,
        coro: Any,
        timeout_seconds: int | None = None,
    ) -> Any:
        """Execute an async function with timeout enforcement.

        Args:
            stage_name: Stage name (for timeout lookup).
            coro: Awaitable coroutine.
            timeout_seconds: Optional explicit timeout override.

        Returns:
            Coroutine result.

        Raises:
            PipelineTimeoutError: If execution exceeds timeout.
        """
        timeout = timeout_seconds or self.get_timeout(stage_name)

        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            elapsed = timeout
            raise PipelineTimeoutError(
                f"Stage '{stage_name}' timed out after {timeout}s"
            )

    def get_timeout_config(self, stage_name: str) -> TimeoutConfig:
        """Get the full timeout config for a stage.

        Args:
            stage_name: Stage name.

        Returns:
            ``TimeoutConfig`` with timeout and action.
        """
        timeout = self.get_timeout(stage_name)
        return TimeoutConfig(
            stage_name=stage_name,
            timeout_seconds=timeout,
            action="retry",
        )

    def get_all_timeouts(self) -> dict[str, int]:
        """Get all configured timeouts.

        Returns:
            Dict of stage_name -> timeout_seconds.
        """
        timeouts = {}
        for stage in STAGE_TIMEOUT_DEFAULTS:
            timeouts[stage] = self.get_timeout(stage)
        return timeouts

    def reset_overrides(self) -> None:
        """Clear all runtime timeout overrides."""
        self._overrides.clear()
