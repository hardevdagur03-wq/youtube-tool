"""Meta generator — Phase 8. AI-powered meta title and description generation."""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

from modules.ai.provider import LLMProvider, ProviderConfig
from modules.ai.provider_factory import create as create_provider
from config.settings import settings

logger = logging.getLogger(__name__)
_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "seo"
_META_PROMPT = "meta_generation.md"


def _load_prompt(name: str, **kwargs: str) -> str:
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing SEO prompt: {path}")
    raw = path.read_text(encoding="utf-8")
    lines = [l for l in raw.splitlines() if not l.startswith("PROMPT_VERSION")]
    base = "\n".join(lines).strip()
    return base.format(**kwargs)


def generate_meta(
    title: str,
    primary_keyword: str = "",
    secondary_keywords: list[str] | None = None,
    topic: str = "",
    audience: str = "",
    content_type: str = "",
    provider: LLMProvider | None = None,
) -> dict[str, str]:
    fallback = {"meta_title": title[:60], "meta_description": title[:160]}
    if not provider:
        key = getattr(settings, "gemini_api_key", "") or ""
        if not key:
            return fallback
        try:
            provider = create_provider("gemini", key, "gemini-2.5-flash")
        except Exception:
            return fallback

    try:
        prompt = _load_prompt(
            _META_PROMPT,
            title=title or "",
            primary_keyword=primary_keyword or "",
            secondary_keywords=", ".join(secondary_keywords or []) or "None",
            topic=topic or title,
            audience=audience or "General",
            content_type=content_type or "article",
        )
        system = "You are an SEO metadata expert. Output ONLY valid JSON."
        data = provider.generate_json(prompt, system)
        meta_title = str(data.get("meta_title", "") or "")[:60]
        meta_description = str(data.get("meta_description", "") or "")[:165]
        return {"meta_title": meta_title, "meta_description": meta_description}
    except Exception as exc:
        logger.warning("Meta generation failed: %s", exc)
        return fallback
