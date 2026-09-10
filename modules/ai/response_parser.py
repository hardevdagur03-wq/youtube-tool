"""JSON response parser — Phase 7. Validates and extracts structured blog output."""

from __future__ import annotations
import json
import logging
import re
from typing import Any

from models.blog_generation import BlogResult, BlogSection, BlogSubSection, CalloutBox, FAQItem, BlogStatistics
from exceptions.blog_errors import BlogInvalidOutput

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def parse_blog(raw: str) -> dict[str, Any]:
    try:
        cleaned = _strip_fence(raw)
        data: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise BlogInvalidOutput(f"JSON parse failed: {exc}")
    if not isinstance(data, dict):
        raise BlogInvalidOutput("Response is not a dict")
    return data


def to_blog_model(data: dict[str, Any]) -> BlogResult:
    sections: list[BlogSection] = []
    for sec in data.get("sections", []):
        subs = [BlogSubSection(heading=s.get("heading", ""), content=s.get("content", "")) for s in sec.get("subsections", []) if isinstance(s, dict)]
        boxes = [CalloutBox(type=b.get("type", "note"), text=b.get("text", "")) for b in sec.get("callout_boxes", []) if isinstance(b, dict)]
        sections.append(BlogSection(heading=sec.get("heading", ""), content=sec.get("content", ""), subsections=subs, callout_boxes=boxes))

    faq = [FAQItem(question=f.get("question", ""), answer=f.get("answer", "")) for f in data.get("faq", []) if isinstance(f, dict) and f.get("question") and f.get("answer")]

    toc = [str(t) for t in data.get("table_of_contents", []) if t]

    full_text = " ".join([data.get("introduction", ""), " ".join(s.content for s in sections), data.get("conclusion", "")])
    wc = len(full_text.split())
    rt = f"{max(1, round(wc / 200))} min" if wc >= 200 else "< 1 min"

    return BlogResult(
        seo_title=data.get("seo_title", data.get("title", "")),
        meta_description=data.get("meta_description", ""),
        slug=data.get("slug", ""),
        introduction=data.get("introduction", ""),
        table_of_contents=toc,
        sections=sections,
        faq=faq,
        conclusion=data.get("conclusion", ""),
        call_to_action=data.get("call_to_action", data.get("cta", "")),
        statistics=BlogStatistics(word_count=wc, reading_time=rt),
    )
