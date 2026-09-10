"""CMS Provider abstraction — common interface for all CMS platforms.

Every CMS provider implements this contract.
Business logic never calls CMS SDKs directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PublishStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    UPDATED = "updated"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class CMSArticle:
    title: str = ""
    content: str = ""
    excerpt: str = ""
    slug: str = ""
    status: PublishStatus = PublishStatus.DRAFT
    featured_image_url: str = ""
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    seo_title: str = ""
    meta_description: str = ""
    focus_keyword: str = ""
    canonical_url: str = ""
    author: str = ""
    published_at: str = ""
    scheduled_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishResult:
    success: bool = False
    provider: str = ""
    url: str = ""
    post_id: str = ""
    status: PublishStatus = PublishStatus.FAILED
    error: str = ""
    published_at: str = ""


class CMSProvider(ABC):
    """Abstract interface for CMS platform integration.

    All CMS providers (WordPress, Ghost, Medium, etc.) implement this.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def authenticate(self) -> bool:
        ...

    @abstractmethod
    async def create_draft(self, article: CMSArticle) -> PublishResult:
        ...

    @abstractmethod
    async def publish(self, article: CMSArticle) -> PublishResult:
        ...

    @abstractmethod
    async def update(self, post_id: str, article: CMSArticle) -> PublishResult:
        ...

    @abstractmethod
    async def delete(self, post_id: str) -> bool:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class MockCMSProvider(CMSProvider):
    """Mock CMS provider for testing."""

    def __init__(self, name: str = "mock_cms", fail: bool = False):
        self._name = name
        self._fail = fail
        self._posts: dict[str, CMSArticle] = {}

    @property
    def provider_name(self) -> str:
        return self._name

    async def authenticate(self) -> bool:
        return not self._fail

    async def create_draft(self, article: CMSArticle) -> PublishResult:
        if self._fail:
            return PublishResult(success=False, provider=self._name, error="Auth failed")
        post_id = f"post_{len(self._posts) + 1}"
        self._posts[post_id] = article
        return PublishResult(
            success=True,
            provider=self._name,
            post_id=post_id,
            status=PublishStatus.DRAFT,
            url=f"https://{self._name}.example.com/draft/{post_id}",
        )

    async def publish(self, article: CMSArticle) -> PublishResult:
        if self._fail:
            return PublishResult(success=False, provider=self._name, error="Publish failed")
        post_id = f"post_{len(self._posts) + 1}"
        self._posts[post_id] = article
        return PublishResult(
            success=True,
            provider=self._name,
            post_id=post_id,
            status=PublishStatus.PUBLISHED,
            url=f"https://{self._name}.example.com/{post_id}",
        )

    async def update(self, post_id: str, article: CMSArticle) -> PublishResult:
        if self._fail:
            return PublishResult(success=False, provider=self._name, error="Update failed")
        if post_id in self._posts:
            self._posts[post_id] = article
            return PublishResult(
                success=True,
                provider=self._name,
                post_id=post_id,
                status=PublishStatus.UPDATED,
            )
        return PublishResult(success=False, provider=self._name, error="Post not found")

    async def delete(self, post_id: str) -> bool:
        if self._fail:
            return False
        return self._posts.pop(post_id, None) is not None

    async def health_check(self) -> bool:
        return not self._fail
