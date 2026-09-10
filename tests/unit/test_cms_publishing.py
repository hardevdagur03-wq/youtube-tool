"""Comprehensive tests for the CMS Publishing Platform."""

from __future__ import annotations

import pytest

from services.publishing.cms_provider import (
    CMSArticle,
    CMSProvider,
    MockCMSProvider,
    PublishResult,
    PublishStatus,
)
from services.publishing.publishing_gateway import (
    PublishJob,
    PublishRequest,
    PublishingGateway,
)


class TestCMSProvider:
    @pytest.mark.asyncio
    async def test_provider_name(self):
        provider = MockCMSProvider("wordpress")
        assert provider.provider_name == "wordpress"

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        provider = MockCMSProvider("test")
        result = await provider.authenticate()
        assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_failure(self):
        provider = MockCMSProvider("test", fail=True)
        result = await provider.authenticate()
        assert result is False

    @pytest.mark.asyncio
    async def test_create_draft(self):
        provider = MockCMSProvider("ghost")
        article = CMSArticle(title="Draft Post", content="Draft content")
        result = await provider.create_draft(article)
        assert result.success is True
        assert result.status == PublishStatus.DRAFT
        assert result.post_id is not None

    @pytest.mark.asyncio
    async def test_publish(self):
        provider = MockCMSProvider("wp")
        article = CMSArticle(title="Published Post", content="Published content")
        result = await provider.publish(article)
        assert result.success is True
        assert result.status == PublishStatus.PUBLISHED
        assert result.url != ""

    @pytest.mark.asyncio
    async def test_update(self):
        provider = MockCMSProvider("test")
        article = CMSArticle(title="Original")
        create = await provider.publish(article)

        updated_article = CMSArticle(title="Updated")
        result = await provider.update(create.post_id, updated_article)
        assert result.success is True
        assert result.status == PublishStatus.UPDATED

    @pytest.mark.asyncio
    async def test_delete(self):
        provider = MockCMSProvider("test")
        article = CMSArticle(title="To Delete")
        create = await provider.publish(article)
        result = await provider.delete(create.post_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        provider = MockCMSProvider("test")
        result = await provider.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check(self):
        provider = MockCMSProvider("test")
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = MockCMSProvider("test", fail=True)
        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_publish_with_metadata(self):
        provider = MockCMSProvider("test")
        article = CMSArticle(
            title="SEO Post",
            content="Content here",
            seo_title="SEO Title",
            meta_description="SEO description",
            focus_keyword="keyword",
            categories=["Tech"],
            tags=["python", "ai"],
        )
        result = await provider.publish(article)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_post(self):
        provider = MockCMSProvider("test")
        article = CMSArticle(title="Ghost")
        result = await provider.update("ghost_post", article)
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_provider_interface_abstract(self):
        with pytest.raises(TypeError):
            CMSProvider()


class TestCMSArticle:
    def test_default_values(self):
        article = CMSArticle()
        assert article.title == ""
        assert article.status == PublishStatus.DRAFT
        assert article.categories == []
        assert article.tags == []

    def test_custom_values(self):
        article = CMSArticle(
            title="Test Post",
            content="Content",
            categories=["Tech"],
            tags=["ai"],
            seo_title="SEO Title",
            status=PublishStatus.PUBLISHED,
        )
        assert article.title == "Test Post"
        assert article.seo_title == "SEO Title"
        assert article.status == PublishStatus.PUBLISHED


class TestPublishResult:
    def test_default_values(self):
        result = PublishResult()
        assert result.success is False
        assert result.provider == ""
        assert result.status == PublishStatus.FAILED

    def test_success_result(self):
        result = PublishResult(
            success=True,
            provider="wordpress",
            url="https://example.com/post",
            post_id="123",
            status=PublishStatus.PUBLISHED,
        )
        assert result.success is True
        assert result.url == "https://example.com/post"


class TestPublishingGateway:
    @pytest.mark.asyncio
    async def test_register_provider(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))
        assert "wp" in gateway._providers

    @pytest.mark.asyncio
    async def test_publish_single_provider(self):
        gateway = PublishingGateway()
        gateway.register_provider("test", MockCMSProvider("test"))
        request = PublishRequest(title="Test", content="Content", providers=["test"])
        job = await gateway.publish(request)
        assert len(job.results) == 1
        assert job.results[0].success is True

    @pytest.mark.asyncio
    async def test_publish_multiple_providers(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))
        gateway.register_provider("ghost", MockCMSProvider("ghost"))

        request = PublishRequest(
            title="Multi CMS",
            content="Content",
            providers=["wp", "ghost"],
        )
        job = await gateway.publish(request)
        assert len(job.results) == 2
        assert all(r.success for r in job.results)

    @pytest.mark.asyncio
    async def test_publish_to_all_providers(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))
        gateway.register_provider("ghost", MockCMSProvider("ghost"))

        request = PublishRequest(title="All", content="Content")
        job = await gateway.publish_to_all(request)
        assert len(job.results) == 2

    @pytest.mark.asyncio
    async def test_publish_with_unregistered_provider(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))

        request = PublishRequest(
            title="Test",
            content="Content",
            providers=["wp", "nonexistent"],
        )
        job = await gateway.publish(request)
        assert len(job.results) == 2
        assert job.results[0].success is True
        assert job.results[1].success is False

    @pytest.mark.asyncio
    async def test_provider_failure_doesnt_affect_others(self):
        gateway = PublishingGateway()
        gateway.register_provider("good", MockCMSProvider("good"))
        gateway.register_provider("bad", MockCMSProvider("bad", fail=True))

        request = PublishRequest(
            title="Mixed",
            content="Content",
            providers=["good", "bad"],
        )
        job = await gateway.publish(request)
        assert job.results[0].success is True
        assert job.results[1].success is False

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        gateway = PublishingGateway()
        gateway.register_provider("good", MockCMSProvider("good"))
        gateway.register_provider("bad", MockCMSProvider("bad", fail=True))

        health = await gateway.health_check()
        assert health["good"] is True
        assert health["bad"] is False

    @pytest.mark.asyncio
    async def test_health_check_single(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))
        health = await gateway.health_check("wp")
        assert health["wp"] is True

    @pytest.mark.asyncio
    async def test_get_job(self):
        gateway = PublishingGateway()
        gateway.register_provider("test", MockCMSProvider("test"))
        request = PublishRequest(title="Track", content="Content", providers=["test"])
        job = await gateway.publish(request)
        assert job.job_id is not None

        fetched = gateway.get_job(job.job_id)
        assert fetched is not None
        assert fetched.job_id == job.job_id

    @pytest.mark.asyncio
    async def test_job_status_tracking(self):
        gateway = PublishingGateway()
        gateway.register_provider("test", MockCMSProvider("test"))
        request = PublishRequest(title="Status", content="Content", providers=["test"])
        job = await gateway.publish(request)
        assert job.status in ("completed", "partial", "pending")
        assert job.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_republish(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))

        create_req = PublishRequest(title="Original", content="Content", providers=["wp"])
        create_job = await gateway.publish(create_req)

        update_req = PublishRequest(title="Updated", content="New content")
        result = await gateway.republish(create_job.results[0].post_id, "wp", update_req)
        assert result.success is True
        assert result.status == PublishStatus.UPDATED

    @pytest.mark.asyncio
    async def test_delete_post(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))

        request = PublishRequest(title="Delete Me", content="Content", providers=["wp"])
        job = await gateway.publish(request)

        result = await gateway.delete_post(job.results[0].post_id, "wp")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_post_wrong_provider(self):
        gateway = PublishingGateway()
        result = await gateway.delete_post("post-1", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_scheduled_publishing_creates_draft(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))

        request = PublishRequest(
            title="Scheduled Post",
            content="Scheduled content",
            scheduled_at="2026-08-01T00:00:00Z",
            providers=["wp"],
        )
        job = await gateway.publish(request)
        assert job.results[0].status == PublishStatus.DRAFT

    @pytest.mark.asyncio
    async def test_immediate_publishing_publishes(self):
        gateway = PublishingGateway()
        gateway.register_provider("wp", MockCMSProvider("wp"))

        request = PublishRequest(
            title="Immediate",
            content="Publish now",
            scheduled_at="",
            providers=["wp"],
        )
        job = await gateway.publish(request)
        assert job.results[0].status == PublishStatus.PUBLISHED


class TestPublishJob:
    def test_default_values(self):
        job = PublishJob()
        assert job.status == "pending"
        assert job.results == []
        assert job.error == ""

    def test_with_results(self):
        job = PublishJob(
            job_id="job-1",
            status="completed",
            results=[
                PublishResult(success=True, provider="wp"),
            ],
        )
        assert job.job_id == "job-1"
        assert len(job.results) == 1


class TestPublishRequest:
    def test_default_values(self):
        req = PublishRequest()
        assert req.providers == []
        assert req.title == ""

    def test_custom_values(self):
        req = PublishRequest(
            title="Custom",
            content="Content",
            providers=["wp", "ghost"],
            categories=["Tech"],
            tags=["ai"],
        )
        assert req.title == "Custom"
        assert len(req.providers) == 2
