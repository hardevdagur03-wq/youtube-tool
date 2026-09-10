"""Schema generator — Phase 8. Generates Schema.org JSON-LD markup."""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

from modules.ai.provider import LLMProvider
from modules.ai.provider_factory import create as create_provider
from models.blog_generation import BlogResult
from config.settings import settings

logger = logging.getLogger(__name__)
_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "seo"
_SCHEMA_PROMPT = "schema_generation.md"


def _load_seo_prompt(name: str) -> str:
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing SEO prompt: {path}")
    raw = path.read_text(encoding="utf-8")
    lines = [l for l in raw.splitlines() if not l.startswith("PROMPT_VERSION")]
    return "\n".join(lines).strip()


def generate(
    blog: BlogResult,
    video_id: str = "",
    primary_keyword: str = "",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    import concurrent.futures
    if not provider:
        key = getattr(settings, "gemini_api_key", "") or ""
        if key:
            try:
                provider = create_provider("gemini", key, "gemini-2.5-flash")
            except Exception as exc:
                logger.debug("Failed to create schema provider: %s", exc)
    if provider:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            fut = pool.submit(_generate_ai, blog, video_id, primary_keyword, tags, metadata, provider)
            try:
                return fut.result(timeout=15)
            except Exception as exc:
                logger.warning("AI schema generation timed out or failed: %s", exc)
    return _generate_algorithmic(blog, video_id, primary_keyword, tags, metadata)


def _generate_ai(
    blog: BlogResult, video_id: str, pk: str, tags: list[str] | None,
    metadata: dict[str, Any] | None, provider: LLMProvider,
) -> dict[str, Any]:
    base = _load_seo_prompt(_SCHEMA_PROMPT)
    faq_json = json.dumps([{"question": f.question, "answer": f.answer} for f in blog.faq])
    prompt = base.format(
        title=blog.seo_title or "",
        description=blog.meta_description or blog.introduction[:200],
        slug=blog.slug or "",
        primary_keyword=pk or "",
        author="YouTube Blog AI",
        published_date=(metadata or {}).get("published_date", ""),
        channel=(metadata or {}).get("channel", ""),
        video_id=video_id or "",
        tags=", ".join(tags or []),
        faq=faq_json,
    )
    system = "You are an SEO structured data expert. Output ONLY valid JSON."
    data = provider.generate_json(prompt, system)
    return data if isinstance(data, dict) else _generate_algorithmic(blog, video_id, pk, tags, metadata)


def _generate_algorithmic(
    blog: BlogResult, video_id: str, pk: str, tags: list[str] | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    url = f"https://youtube.com/watch?v={video_id}" if video_id else ""
    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": blog.seo_title or "",
        "description": blog.meta_description or blog.introduction[:200],
        "url": url,
        "author": {"@type": "Person", "name": "YouTube Blog AI"},
    }
    blog_posting = {**article, "@type": "BlogPosting"}
    faq_page = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": f.question, "acceptedAnswer": {"@type": "Answer", "text": f.answer}} for f in blog.faq]} if blog.faq else {}
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": s.heading, "item": f"{url}#{s.heading.lower().replace(' ', '-')}"} for i, s in enumerate(blog.sections[:5])]} if blog.sections else {}
    video = {"@context": "https://schema.org", "@type": "VideoObject", "name": blog.seo_title or "", "description": blog.meta_description or "", "contentUrl": url} if video_id else {}
    return {"article": article, "blog_posting": blog_posting, "faq_page": faq_page, "breadcrumb_list": breadcrumb, "video_object": video}


def generate_faq_schema(faq: list[dict[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f.get("question", ""), "acceptedAnswer": {"@type": "Answer", "text": f.get("answer", "")}}
            for f in faq if f.get("question") and f.get("answer")
        ],
    }
