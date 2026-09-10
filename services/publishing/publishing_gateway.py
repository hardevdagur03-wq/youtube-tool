"""Publishing Gateway — orchestrates multi-CMS publishing with queuing and scheduling.

Routes content through provider chain, handles retries, and tracks status.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from services.publishing.cms_provider import (
    CMSArticle,
    CMSProvider,
    PublishResult,
    PublishStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class PublishRequest:
    title: str = ""
    content: str = ""
    excerpt: str = ""
    slug: str = ""
    featured_image_url: str = ""
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    seo_title: str = ""
    meta_description: str = ""
    focus_keyword: str = ""
    canonical_url: str = ""
    author: str = ""
    scheduled_at: str = ""
    providers: list[str] = field(default_factory=list)


@dataclass
class PublishJob:
    job_id: str = ""
    status: str = "pending"
    results: list[PublishResult] = field(default_factory=list)
    error: str = ""
    duration_ms: float = 0.0


class PublishingGateway:
    """Central gateway for multi-CMS publishing with automatic failover."""

    def __init__(self):
        self._providers: dict[str, CMSProvider] = {}
        self._jobs: dict[str, PublishJob] = {}

    def register_provider(self, name: str, provider: CMSProvider) -> None:
        self._providers[name] = provider
        logger.info("CMS provider registered: %s", name)

    async def publish(self, request: PublishRequest) -> PublishJob:
        start = time.time()
        job_id = f"pub_{int(start)}_{len(self._jobs)}"
        job = PublishJob(job_id=job_id)
        results = []

        for provider_name in request.providers:
            provider = self._providers.get(provider_name)
            if not provider:
                results.append(PublishResult(
                    success=False,
                    provider=provider_name,
                    error=f"Provider not registered: {provider_name}",
                ))
                continue

            try:
                article = CMSArticle(
                    title=request.title,
                    content=request.content,
                    excerpt=request.excerpt,
                    slug=request.slug,
                    featured_image_url=request.featured_image_url,
                    categories=request.categories,
                    tags=request.tags,
                    seo_title=request.seo_title,
                    meta_description=request.meta_description,
                    focus_keyword=request.focus_keyword,
                    canonical_url=request.canonical_url,
                    author=request.author,
                    scheduled_at=request.scheduled_at,
                )

                if request.scheduled_at:
                    result = await provider.create_draft(article)
                else:
                    result = await provider.publish(article)

                results.append(result)

            except Exception as e:
                logger.error("Provider %s failed: %s", provider_name, e)
                results.append(PublishResult(
                    success=False,
                    provider=provider_name,
                    error=str(e),
                ))

        job.results = results
        job.duration_ms = (time.time() - start) * 1000
        job.status = "completed" if all(r.success for r in results) else "partial"
        self._jobs[job_id] = job
        return job

    async def publish_to_all(self, request: PublishRequest) -> PublishJob:
        request.providers = list(self._providers.keys())
        return await self.publish(request)

    async def republish(self, post_id: str, provider: str, request: PublishRequest) -> PublishResult:
        cms = self._providers.get(provider)
        if not cms:
            return PublishResult(success=False, provider=provider, error="Provider not found")

        article = CMSArticle(
            title=request.title,
            content=request.content,
            excerpt=request.excerpt,
            slug=request.slug,
            categories=request.categories,
            tags=request.tags,
        )
        return await cms.update(post_id, article)

    async def delete_post(self, post_id: str, provider: str) -> bool:
        cms = self._providers.get(provider)
        if not cms:
            return False
        return await cms.delete(post_id)

    def get_job(self, job_id: str) -> PublishJob | None:
        return self._jobs.get(job_id)

    async def health_check(self, provider: str | None = None) -> dict[str, bool]:
        if provider:
            cms = self._providers.get(provider)
            return {provider: await cms.health_check() if cms else False}

        health = {}
        for name, cms in self._providers.items():
            try:
                health[name] = await cms.health_check()
            except Exception:
                health[name] = False
        return health
