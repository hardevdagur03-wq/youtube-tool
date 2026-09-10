"""Performance Engineering — Pipeline performance monitoring middleware.

Adds performance tracking to the FastAPI application.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from performance_engineering.monitoring import LatencyProfiler

logger = logging.getLogger(__name__)

# Global profiler instance
_profiler = LatencyProfiler()


def get_profiler() -> LatencyProfiler:
    """Get the global latency profiler instance."""
    return _profiler


async def performance_middleware(request: Any, call_next: Any) -> Any:
    """FastAPI middleware for tracking request performance.

    Usage::

        app.middleware("http")(performance_middleware)
    """
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    endpoint = f"{request.method} {request.url.path}"
    logger.debug("Performance: %s took %.0fms", endpoint, duration_ms)

    response.headers["X-Performance-Ms"] = str(int(duration_ms))
    return response
