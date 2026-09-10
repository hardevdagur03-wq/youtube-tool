"""Tests for the Infrastructure Layer."""

from __future__ import annotations

import pytest

from domain.entities import Project, Video
from domain.value_objects import PipelineStage, PipelineStatus, VideoId
from infrastructure.caching.abstraction import CacheService, InMemoryCache
from infrastructure.config.provider import AppConfig, Config, ConfigProvider, Environment
from infrastructure.di.container import ServiceRegistry, container
from infrastructure.feature_flags.flags import FeatureFlagManager, feature_flags
from infrastructure.repositories.memory_repos import (
    InMemoryUnitOfWork,
)


class TestInMemoryUnitOfWork:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_video(self):
        uow = InMemoryUnitOfWork()
        video = Video(video_id=VideoId("dQw4w9WgXcQ"))

        saved = await uow.videos.save(video)
        assert saved.video_id == VideoId("dQw4w9WgXcQ")

        retrieved = await uow.videos.get_by_video_id(VideoId("dQw4w9WgXcQ"))
        assert retrieved is not None
        assert retrieved.id == video.id

    @pytest.mark.asyncio
    async def test_save_and_retrieve_project(self):
        uow = InMemoryUnitOfWork()
        project = Project(video_id=VideoId("dQw4w9WgXcQ"))

        saved = await uow.projects.save(project)
        assert saved.video_id == VideoId("dQw4w9WgXcQ")

        retrieved = await uow.projects.get_by_id(project.id)
        assert retrieved is not None
        assert retrieved.status == PipelineStatus.PENDING

    @pytest.mark.asyncio
    async def test_commit_and_rollback(self):
        uow = InMemoryUnitOfWork()
        video = Video(video_id=VideoId("dQw4w9WgXcQ"))
        await uow.videos.save(video)

        await uow.commit()
        assert uow._committed is True

        await uow.rollback()
        assert uow._committed is True

    @pytest.mark.asyncio
    async def test_list_projects_with_status_filter(self):
        uow = InMemoryUnitOfWork()
        for _ in range(3):
            p = Project(video_id=VideoId("dQw4w9WgXcQ"))
            await uow.projects.save(p)

        running = Project(video_id=VideoId("dQw4w9WgXcQ"))
        running.status = PipelineStatus.RUNNING
        await uow.projects.save(running)

        results = await uow.projects.list_all(status=PipelineStatus.RUNNING)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with InMemoryUnitOfWork() as uow:
            video = Video(video_id=VideoId("dQw4w9WgXcQ"))
            await uow.videos.save(video)
        assert uow._committed is False

    @pytest.mark.asyncio
    async def test_search_video(self):
        uow = InMemoryUnitOfWork()
        v1 = Video(video_id=VideoId("dQw4w9WgXcQ"), title="Machine Learning Guide")
        v2 = Video(video_id=VideoId("abc123def45"), title="Python Tutorial")
        await uow.videos.save(v1)
        await uow.videos.save(v2)

        results = await uow.videos.search("machine")
        assert len(results) == 1
        assert results[0].title == "Machine Learning Guide"


class TestCacheService:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = CacheService()
        await cache.set("test", "key1", "value1")
        val = await cache.get("test", "key1")
        assert val == "value1"

    @pytest.mark.asyncio
    async def test_miss_returns_none(self):
        cache = CacheService()
        val = await cache.get("test", "nonexistent")
        assert val is None

    @pytest.mark.asyncio
    async def test_delete(self):
        cache = CacheService()
        await cache.set("test", "key1", "value1")
        deleted = await cache.delete("test", "key1")
        assert deleted is True
        val = await cache.get("test", "key1")
        assert val is None

    @pytest.mark.asyncio
    async def test_get_or_set_with_factory(self):
        cache = CacheService()

        async def factory():
            return "computed_value"

        val = await cache.get_or_set("test", "key1", factory)
        assert val == "computed_value"

        val2 = await cache.get_or_set("test", "key1", factory)
        assert val2 == "computed_value"

    @pytest.mark.asyncio
    async def test_stats(self):
        cache = CacheService()
        await cache.get("ns", "miss1")
        await cache.get("ns", "miss2")
        await cache.set("ns", "hit", "val")
        await cache.get("ns", "hit")

        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 2

    @pytest.mark.asyncio
    async def test_clear_namespace(self):
        cache = CacheService()
        await cache.set("ns1", "k", "v1")
        await cache.set("ns2", "k", "v2")
        await cache.clear_namespace("ns1")
        assert await cache.get("ns1", "k") is None
        assert await cache.get("ns2", "k") == "v2"


class TestInMemoryCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        backend = InMemoryCache()
        await backend.set("key", "value")
        val = await backend.get("key")
        assert val == "value"

    @pytest.mark.asyncio
    async def test_delete(self):
        backend = InMemoryCache()
        await backend.set("key", "value")
        assert await backend.delete("key") is True
        assert await backend.get("key") is None

    @pytest.mark.asyncio
    async def test_exists(self):
        backend = InMemoryCache()
        await backend.set("key", "value")
        assert await backend.exists("key") is True
        await backend.delete("key")
        assert await backend.exists("key") is False

    @pytest.mark.asyncio
    async def test_clear(self):
        backend = InMemoryCache()
        await backend.set("k1", "v1")
        await backend.set("k2", "v2")
        await backend.clear()
        assert await backend.get("k1") is None
        assert await backend.get("k2") is None


class TestServiceRegistry:
    def test_register_and_resolve(self):
        reg = ServiceRegistry()
        reg.register("greeter", lambda c: "Hello, World!")
        result = reg.resolve("greeter")
        assert result == "Hello, World!"

    def test_singleton_returns_same_instance(self):
        reg = ServiceRegistry()
        reg.register("counter", lambda c: object())
        instance1 = reg.resolve("counter")
        instance2 = reg.resolve("counter")
        assert instance1 is instance2

    def test_nonsingleton_returns_new_instance(self):
        reg = ServiceRegistry()
        reg.register("counter", lambda c: object(), singleton=False)
        instance1 = reg.resolve("counter")
        instance2 = reg.resolve("counter")
        assert instance1 is not instance2

    def test_register_instance(self):
        reg = ServiceRegistry()
        obj = {"key": "value"}
        reg.register_instance("config", obj)
        assert reg.resolve("config") is obj

    def test_resolve_unregistered(self):
        reg = ServiceRegistry()
        with pytest.raises(KeyError):
            reg.resolve("nonexistent")

    def test_has(self):
        reg = ServiceRegistry()
        reg.register("svc", lambda c: 42)
        assert reg.has("svc") is True
        assert reg.has("other") is False

    def test_clear(self):
        reg = ServiceRegistry()
        reg.register("svc", lambda c: 42)
        reg.clear()
        assert reg.has("svc") is False


class TestConfigProvider:
    def test_load_with_defaults(self):
        config = ConfigProvider.load()
        assert config is not None
        assert isinstance(config, AppConfig)
        assert config.environment == Environment.LOCAL

    def test_config_singleton(self):
        Config.reload()
        config1 = Config.get()
        config2 = Config.get()
        assert config1 is config2

    def test_config_set(self):
        test_config = AppConfig(environment=Environment.TESTING)
        Config.set(test_config)
        assert Config.get().environment == Environment.TESTING


class TestFeatureFlags:
    def test_default_flags_loaded(self):
        assert feature_flags.is_enabled("gemini_provider") is True
        assert feature_flags.is_enabled("pipeline_v2") is False

    def test_register_custom_flag(self):
        fm = FeatureFlagManager()
        from infrastructure.feature_flags.flags import FeatureFlag
        fm.register(FeatureFlag(key="test_flag", enabled=True))
        assert fm.is_enabled("test_flag") is True

    def test_get_all(self):
        fm = FeatureFlagManager()
        flags = fm.get_all()
        assert len(flags) > 0

    def test_update_flag(self):
        fm = FeatureFlagManager()
        fm.update("pipeline_v2", True)
        assert fm.is_enabled("pipeline_v2") is True


import pytest
