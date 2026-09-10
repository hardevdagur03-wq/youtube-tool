"""Blog metadata extraction — reading time, word count, slug, tags.

Generates all metadata fields that accompany a blog post.
"""

from __future__ import annotations
import logging
import re
from typing import Any

from models.blog_generation import BlogMetadata

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def _estimate_reading_time(word_count: int, wpm: int = 200) -> str:
    if word_count <= 0:
        return "< 1 min"
    minutes = word_count / wpm
    if minutes < 1:
        return "< 1 min"
    mins = round(minutes)
    return f"{mins} min" if mins == 1 else f"{mins} mins"


def extract_metadata(
    title: str,
    sections_markdown: str,
    data: dict[str, Any] | None = None,
) -> BlogMetadata:
    """Extract blog metadata from generated content.

    Args:
        title: Blog title.
        sections_markdown: Full markdown content of the blog body.
        data: Optional parsed blog data for additional metadata fields.

    Returns:
        Populated BlogMetadata object.
    """
    word_count = len(sections_markdown.split()) if sections_markdown else 0
    reading_time = _estimate_reading_time(word_count)

    meta_raw = data.get("metadata", {}) if data else {}

    slug = str(meta_raw.get("slug", "")) if meta_raw.get("slug") else _slugify(title)
    category = str(meta_raw.get("category", ""))
    tags = [str(t) for t in meta_raw.get("tags", []) if t] if meta_raw.get("tags") else []

    primary_keyword = ""
    if data:
        kw = data.get("keywords", data.get("metadata", {}))
        if isinstance(kw, dict):
            primary_keyword = str(kw.get("primary", kw.get("primary_keyword", "")))

    return BlogMetadata(
        word_count=word_count,
        reading_time=reading_time,
        slug=slug,
        category=category,
        tags=tags,
        primary_keyword=primary_keyword,
    )
