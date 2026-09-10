"""Section generator — Phase 7. Extracts and validates sections from LLM output."""

from __future__ import annotations
import logging
from typing import Any

from models.blog_generation import BlogSection, BlogSubSection, CalloutBox

logger = logging.getLogger(__name__)


def extract(data: dict[str, Any]) -> list[BlogSection]:
    raw = data.get("sections", [])
    sections: list[BlogSection] = []
    for i, sec in enumerate(raw):
        if not isinstance(sec, dict):
            continue
        heading = str(sec.get("heading", "")).strip()
        content = str(sec.get("content", "")).strip()
        if not heading and not content:
            continue
        subs = []
        for sub in sec.get("subsections", []):
            if isinstance(sub, dict):
                sh = str(sub.get("heading", "")).strip()
                sc = str(sub.get("content", "")).strip()
                if sh or sc:
                    subs.append(BlogSubSection(heading=sh, content=sc))
        boxes = []
        for b in sec.get("callout_boxes", []):
            if isinstance(b, dict):
                bt = str(b.get("type", "note")).strip()
                bx = str(b.get("text", "")).strip()
                if bx:
                    boxes.append(CalloutBox(type=bt, text=bx))
        sections.append(BlogSection(heading=heading, content=content, subsections=subs, callout_boxes=boxes))
    return sections
