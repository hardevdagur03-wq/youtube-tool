"""Prompt management — Phase 7. Versioned, separated from code, A/B test ready."""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "blog"
_CACHE: dict[str, str] = {}
_VERSION = "7.0.0"
_VARIANT = "A"


def _load(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt: {path}")
    raw = path.read_text(encoding="utf-8")
    return "\n".join(l for l in raw.splitlines() if not l.startswith("PROMPT_VERSION")).strip()


def get(key: str) -> str:
    k = f"{key}_{_VARIANT}"
    if k not in _CACHE:
        _CACHE[k] = _load(key)
    return _CACHE[k]


def set_variant(v: str) -> None:
    global _VARIANT
    _VARIANT = v


def version() -> str:
    return _VERSION


def _val(d: dict | None, *keys: str, default: str = "") -> str:
    for k in keys:
        if isinstance(d, dict) and k in d and d[k]:
            v = d[k]
            if isinstance(v, list):
                return ", ".join(str(x) for x in v)
            return str(v)
    return default


def build_blog_prompt(
    transcript: str,
    metadata: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
    max_chars: int = 40000,
) -> str:
    a = analysis or {}
    m = metadata or {}
    kw = a.get("keywords", {})
    en = a.get("entities", {})
    sm = a.get("summary", {})

    excerpt = transcript[:max_chars]
    if len(transcript) > max_chars:
        excerpt += "\n\n[Truncated.]"

    return get("blog_generation.md").format(
        title=_val(m, "title", "name"),
        channel=_val(m, "channel", "channel_title"),
        published_date=_val(m, "published_date", "published_at"),
        duration=_val(m, "duration"),
        tags=_val(m, "tags"),
        category=_val(a, "category"),
        primary_topic=_val(a, "primary_topic"),
        secondary_topics=_val(a, "secondary_topics"),
        search_intent=_val(a, "search_intent"),
        target_audience=_val(a, "target_audience"),
        difficulty=_val(a, "difficulty"),
        industry=_val(a, "industry"),
        content_type=_val(a, "content_type"),
        executive_summary=_val(sm, "executive", "short"),
        primary_keyword=_val(kw, "primary", a.get("primary_topic", "")),
        secondary_keywords=_val(kw, "secondary"),
        long_tail_keywords=_val(kw, "long_tail"),
        semantic_keywords=", ".join((kw.get("semantic", []) + kw.get("lsi", []))[:10]),
        people=_val(en, "people"),
        companies=_val(en, "companies"),
        technologies=_val(en, "technologies"),
        products=_val(en, "products"),
        frameworks=_val(en, "frameworks"),
        outline_sections=_val(a.get("outline", {}), "sections"),
        important_quotes="\n".join(sm.get("important_facts", []) + sm.get("key_insights", [])) or "See transcript.",
        transcript=excerpt,
    )


def build_faq_prompt(transcript: str, analysis: dict[str, Any] | None, max_chars: int = 30000) -> str:
    a = analysis or {}
    sm = a.get("summary", {})
    excerpt = transcript[:max_chars]
    if len(transcript) > max_chars:
        excerpt += "\n\n[Truncated.]"
    return get("faq.md").format(
        primary_topic=_val(a, "primary_topic"),
        target_audience=_val(a, "target_audience"),
        key_insights="\n".join(sm.get("key_insights", [])) or "See transcript.",
        important_facts="\n".join(sm.get("important_facts", [])) or "See transcript.",
        transcript=excerpt,
    )


def build_cta_prompt(analysis: dict[str, Any] | None) -> str:
    a = analysis or {}
    return get("cta.md").format(
        primary_topic=_val(a, "primary_topic"),
        content_type=_val(a, "content_type"),
        target_audience=_val(a, "target_audience"),
        industry=_val(a, "industry"),
    )
