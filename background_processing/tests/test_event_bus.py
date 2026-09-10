"""Tests for EventBus — Redis Pub/Sub for real-time events."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from background_processing.event_bus import EventBus, EventType


@pytest.fixture
def event_bus():
    return EventBus()


class TestEventBus:
    async def test_publish(self):
        redis = AsyncMock()
        redis.publish = AsyncMock(return_value=2)
        bus = EventBus(redis_client=redis)
        count = await bus.publish("test:channel", {"msg": "hello"})
        assert count == 2

    async def test_publish_progress(self):
        redis = AsyncMock()
        redis.publish = AsyncMock(return_value=1)
        bus = EventBus(redis_client=redis)
        count = await bus.publish_progress("proj-1", "job-1", 50.0, "Halfway")
        assert count == 1

    async def test_publish_event(self):
        redis = AsyncMock()
        redis.publish = AsyncMock(return_value=1)
        bus = EventBus(redis_client=redis)
        count = await bus.publish_event("proj-1", EventType.JOB_CREATED, {"job_id": "j1"})
        assert count == 1

    async def test_publish_system(self):
        redis = AsyncMock()
        redis.publish = AsyncMock(return_value=1)
        bus = EventBus(redis_client=redis)
        count = await bus.publish_system(EventType.WORKER_ONLINE, {"worker": "w1"})
        assert count == 1

    async def test_subscribe(self):
        redis = MagicMock()
        pubsub_instance = AsyncMock()
        pubsub_instance.psubscribe = AsyncMock()
        pubsub_instance.punsubscribe = AsyncMock()
        pubsub_instance.close = AsyncMock()
        redis.pubsub.return_value = pubsub_instance

        bus = EventBus(redis_client=redis)
        handler = AsyncMock()
        await bus.subscribe("progress:*", handler)
        assert "progress:*" in bus._handlers
        assert len(bus._handlers["progress:*"]) == 1
        pubsub_instance.psubscribe.assert_called_once()

    async def test_subscribe_multiple_handlers(self):
        redis = MagicMock()
        pubsub_instance = AsyncMock()
        pubsub_instance.psubscribe = AsyncMock()
        redis.pubsub.return_value = pubsub_instance

        bus = EventBus(redis_client=redis)
        h1 = AsyncMock()
        h2 = AsyncMock()
        await bus.subscribe("events:*", h1)
        await bus.subscribe("events:*", h2)
        assert len(bus._handlers["events:*"]) == 2

    async def test_unsubscribe(self):
        redis = MagicMock()
        pubsub_instance = AsyncMock()
        pubsub_instance.psubscribe = AsyncMock()
        pubsub_instance.punsubscribe = AsyncMock()
        redis.pubsub.return_value = pubsub_instance

        bus = EventBus(redis_client=redis)
        await bus.subscribe("progress:*", AsyncMock())
        await bus.unsubscribe("progress:*")
        assert "progress:*" not in bus._handlers

    async def test_close(self):
        redis = MagicMock()
        pubsub_instance = AsyncMock()
        pubsub_instance.psubscribe = AsyncMock()
        pubsub_instance.close = AsyncMock()
        redis.pubsub.return_value = pubsub_instance

        bus = EventBus(redis_client=redis)
        await bus.subscribe("progress:*", AsyncMock())
        await bus.close()
        assert bus._pubsub is None

    async def test_get_subscriber_count(self):
        redis = AsyncMock()
        redis.pubsub_numsub = AsyncMock(return_value={"test:ch": 3})
        bus = EventBus(redis_client=redis)
        count = await bus.get_subscriber_count("test:ch")
        assert count == 3

    async def test_get_subscriber_count_zero(self):
        redis = AsyncMock()
        redis.pubsub_numsub = AsyncMock(return_value={"test:ch": 0})
        bus = EventBus(redis_client=redis)
        count = await bus.get_subscriber_count("test:ch")
        assert count == 0

    async def test_multiple_publishes(self):
        redis = AsyncMock()
        redis.publish = AsyncMock(return_value=1)
        bus = EventBus(redis_client=redis)
        for i in range(5):
            await bus.publish(f"channel:{i}", {"idx": i})
        assert redis.publish.call_count == 5
