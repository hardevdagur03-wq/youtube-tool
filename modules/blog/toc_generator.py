"""Table of contents — Phase 7."""

from __future__ import annotations
from typing import Any

from models.blog_generation import BlogSection


def generate(sections: list[BlogSection], data: dict[str, Any] | None = None) -> list[str]:
    toc: list[str] = []
    for s in sections:
        if s.heading:
            toc.append(s.heading)
            for sub in s.subsections:
                if sub.heading:
                    toc.append(f"  - {sub.heading}")
    if not toc and data:
        toc = [str(t) for t in data.get("table_of_contents", []) if t]
    return toc
