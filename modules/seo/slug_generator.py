"""Slug generator — Phase 8. Generates SEO-friendly URL slugs."""

from __future__ import annotations
import re
from typing import Any


def generate(title: str, primary_keyword: str = "") -> str:
    slug = title if title else primary_keyword
    if not slug:
        return ""
    slug = slug.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:80]


def from_blog(seo_title: str, primary_keyword: str = "", fallback: str = "blog-post") -> str:
    return generate(seo_title or primary_keyword or fallback)
