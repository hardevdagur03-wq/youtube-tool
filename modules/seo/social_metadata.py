"""Social metadata — Phase 8. Open Graph and Twitter Card generation."""

from __future__ import annotations
from typing import Any

from models.blog_generation import BlogResult


def generate_og(blog: BlogResult, primary_keyword: str = "") -> dict[str, str]:
    return {
        "title": blog.seo_title[:95] or "",
        "description": (blog.meta_description or blog.introduction[:200])[:200],
        "image": "",
        "type": "article",
    }


def generate_twitter(blog: BlogResult, primary_keyword: str = "") -> dict[str, str]:
    return {
        "title": blog.seo_title[:70] or "",
        "description": (blog.meta_description or blog.introduction[:160])[:200],
        "image": "",
        "card_type": "summary_large_image",
    }


def generate_all(blog: BlogResult, primary_keyword: str = "") -> dict[str, Any]:
    return {
        "open_graph": generate_og(blog, primary_keyword),
        "twitter_card": generate_twitter(blog, primary_keyword),
    }
