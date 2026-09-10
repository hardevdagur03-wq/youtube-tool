"""SSE Manager — Server-Sent Events for streaming pipeline output.

Supports streaming transcript output, AI generation, blog sections,
pipeline progress, and export progress via SSE.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)


class SSEManager:
    """Server-Sent Events manager for streaming pipeline output.

    Manages SSE connections, events, and cleanup.
    Supports multiple concurrent subscribers per event stream.

    Usage::

        sse = SSEManager()
        async for event in sse.subscribe("pipeline_123"):
            # send event to client
            yield f"data: {json.dumps(event)}"
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._enabled = self._config.streaming_enabled
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    async def publish(
        self, stream_key: str, data: Any, event_type: str = "message"
    ) -> int:
        """Publish an event to all subscribers of a stream.

        Args:
            stream_key: Stream identifier (e.g. pipeline_id).
            data: Event data (will be JSON-serialized).
            event_type: SSE event type.

        Returns:
            Number of subscribers that received the event.
        """
        if not self._enabled:
            return 0

        subscribers = self._subscribers.get(stream_key, [])
        message = {"type": event_type, "data": data, "timestamp": time.time()}

        delivered = 0
        for queue in subscribers:
            try:
                await asyncio.wait_for(queue.put(message), timeout=1.0)
                delivered += 1
            except (asyncio.TimeoutError, Exception):
                pass

        return delivered

    async def subscribe(
        self, stream_key: str, max_queue_size: int = 100
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to a stream and yield events.

        Args:
            stream_key: Stream identifier.
            max_queue_size: Max buffered events per subscriber.

        Yields:
            Event dicts with type, data, and timestamp.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        if stream_key not in self._subscribers:
            self._subscribers[stream_key] = []
        self._subscribers[stream_key].append(queue)

        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"type": "keepalive", "data": None, "timestamp": time.time()}
        except asyncio.CancelledError:
            pass
        finally:
            # Cleanup on disconnect
            if stream_key in self._subscribers:
                self._subscribers[stream_key] = [
                    q for q in self._subscribers[stream_key] if q is not queue
                ]
                if not self._subscribers[stream_key]:
                    del self._subscribers[stream_key]

    def subscriber_count(self, stream_key: str) -> int:
        """Get the number of subscribers for a stream.

        Args:
            stream_key: Stream identifier.

        Returns:
            Subscriber count.
        """
        return len(self._subscribers.get(stream_key, []))

    def get_stats(self) -> dict[str, Any]:
        """Get SSE manager statistics."""
        return {
            "active_streams": len(self._subscribers),
            "total_subscribers": sum(len(s) for s in self._subscribers.values()),
            "enabled": self._enabled,
        }
