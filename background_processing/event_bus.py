"""Event Bus — Redis Pub/Sub for real-time progress events and inter-worker communication.

No direct worker-to-worker communication.
All events flow through the event bus.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from redis.asyncio import Redis

from background_processing.config import BackgroundProcessingConfig

logger = logging.getLogger(__name__)


class EventBus:
    """Redis Pub/Sub event bus for distributed progress events.

    Workers emit progress events via Redis channels.
    The frontend receives them via WebSocket/SSE relay.

    Channel naming convention:
        progress:<project_id>:<job_id>  — per-job progress
        events:<project_id>             — project-level events (job lifecycle)
        system:<event_type>             — system-wide events (worker health, etc.)
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        config: BackgroundProcessingConfig | None = None,
    ) -> None:
        self._config = config or BackgroundProcessingConfig.from_env()
        self._redis = redis_client
        self._pubsub: Any = None
        self._handlers: dict[str, list[Callable]] = {}

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self._config.event_bus_redis_url or self._config.redis_url,
                socket_timeout=self._config.redis_socket_timeout,
                socket_connect_timeout=self._config.redis_socket_connect_timeout,
                decode_responses=True,
            )
        return self._redis

    async def publish(self, channel: str, data: dict[str, Any]) -> int:
        """Publish a JSON-encoded message to a Redis channel.

        Returns:
            Number of subscribers that received the message.
        """
        redis = await self._get_redis()
        message = json.dumps(data, default=str)
        result = await redis.publish(channel, message)
        logger.debug("Published to %s: %d subscribers", channel, result)
        return result

    async def publish_progress(
        self,
        project_id: str,
        job_id: str,
        pct: float,
        message: str = "",
        stage: str = "",
        detail: dict[str, Any] | None = None,
    ) -> int:
        """Publish a per-job progress event."""
        return await self.publish(
            f"progress:{project_id}:{job_id}",
            {
                "type": "progress",
                "project_id": project_id,
                "job_id": job_id,
                "pct": pct,
                "message": message,
                "stage": stage,
                "detail": detail or {},
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
            },
        )

    async def publish_event(
        self,
        project_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> int:
        """Publish a project-level lifecycle event."""
        return await self.publish(
            f"events:{project_id}",
            {
                "type": event_type,
                "project_id": project_id,
                "data": data or {},
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
            },
        )

    async def publish_system(
        self, event_type: str, data: dict[str, Any] | None = None
    ) -> int:
        """Publish a system-wide event."""
        return await self.publish(
            f"system:{event_type}",
            {
                "type": event_type,
                "data": data or {},
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
            },
        )

    async def subscribe(self, channel: str, handler: Callable) -> None:
        """Register a handler for messages on a channel pattern.

        The handler receives the parsed dict data.
        Supports glob patterns like ``progress:*``.
        """
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

        redis = await self._get_redis()
        if self._pubsub is None:
            self._pubsub = redis.pubsub()
        await self._pubsub.psubscribe(**{channel: self._on_message})

    async def _on_message(self, message: dict[str, Any]) -> None:
        """Internal message dispatcher."""
        if message.get("type") != "pmessage":
            return
        channel = message.get("channel", "")
        data_raw = message.get("data", "")
        if isinstance(data_raw, str):
            try:
                data = json.loads(data_raw)
            except (json.JSONDecodeError, TypeError):
                data = {"raw": data_raw}
        else:
            data = data_raw

        handlers = self._handlers.get(channel, [])
        for handler in handlers:
            try:
                await handler(data)
            except Exception:
                logger.exception("Event handler failed for channel %s", channel)

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel pattern."""
        self._handlers.pop(channel, None)
        if self._pubsub:
            await self._pubsub.punsubscribe(channel)

    async def close(self) -> None:
        """Close the pubsub connection."""
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None

    async def get_subscriber_count(self, channel: str) -> int:
        """Get the number of subscribers on a channel."""
        redis = await self._get_redis()
        result = await redis.pubsub_numsub(channel)
        return result.get(channel, 0) if isinstance(result, dict) else 0


# Standard event type constants
class EventType:
    JOB_CREATED = "job.created"
    JOB_QUEUED = "job.queued"
    JOB_STARTED = "job.started"
    JOB_PROGRESS = "job.progress"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    JOB_RETRYING = "job.retrying"
    JOB_RETRY_STARTED = "job.retry_started"
    JOB_RETRY_FINISHED = "job.retry_finished"
    JOB_DEAD_LETTER = "job.dead_letter"
    JOB_RECOVERED = "job.recovered"
    STAGE_STARTED = "stage.started"
    STAGE_COMPLETED = "stage.completed"
    STAGE_FAILED = "stage.failed"
    WORKER_ONLINE = "worker.online"
    WORKER_OFFLINE = "worker.offline"
    WORKER_HEALTH = "worker.health"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus(redis_client: Redis | None = None) -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus(redis_client=redis_client)
    return _event_bus
