"""Keyword analyzer — Phase 8. Full keyword analysis with placement tracking."""

from __future__ import annotations
import re
from typing import Any

from models.blog_generation import BlogResult


def analyze(
    blog: BlogResult,
    primary: str = "",
    secondary: list[str] | None = None,
    long_tail: list[str] | None = None,
    lsi: list[str] | None = None,
) -> dict[str, Any]:
    full = _full_text(blog)
    wc = len(full.split())
    pk = primary.lower().strip() if primary else ""
    sec = [k.lower().strip() for k in (secondary or []) if k.strip()]
    lt = [k.lower().strip() for k in (long_tail or []) if k.strip()]
    lsi_kw = [k.lower().strip() for k in (lsi or []) if k.strip()]

    result: dict[str, Any] = {
        "primary": primary,
        "secondary": sec,
        "long_tail": lt,
        "lsi": lsi_kw,
        "density": {"primary": 0.0, "secondary": {}},
        "in_title": False,
        "in_meta": False,
        "in_intro": False,
        "in_headings": [],
        "in_first_paragraph": False,
        "in_last_paragraph": False,
    }

    if not pk or wc == 0:
        return result

    count = full.lower().count(pk)
    result["density"]["primary"] = round((count / wc) * 100, 2)
    result["in_title"] = pk in blog.seo_title.lower()
    result["in_meta"] = pk in blog.meta_description.lower()
    result["in_intro"] = pk in blog.introduction.lower()

    for s in blog.sections:
        if pk in s.heading.lower():
            result["in_headings"].append(s.heading)

    paras = full.split("\n\n")
    if paras:
        result["in_first_paragraph"] = pk in paras[0].lower()
        result["in_last_paragraph"] = pk in paras[-1].lower()

    sec_density: dict[str, float] = {}
    for kw in sec:
        c = full.lower().count(kw)
        sec_density[kw] = round((c / wc) * 100, 3) if wc else 0.0
    result["density"]["secondary"] = sec_density

    return result


def _full_text(blog: BlogResult) -> str:
    parts = [blog.seo_title, blog.introduction]
    for s in blog.sections:
        parts.append(s.content)
        for sub in s.subsections:
            parts.append(sub.content)
    parts.append(blog.conclusion)
    return " ".join(parts)
