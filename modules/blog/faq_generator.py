"""FAQ generator — Phase 7."""

from __future__ import annotations
import logging
from typing import Any

from models.blog_generation import FAQItem

logger = logging.getLogger(__name__)


def extract(data: dict[str, Any]) -> list[FAQItem]:
    items: list[FAQItem] = []
    for f in data.get("faq", []):
        if isinstance(f, dict):
            q = str(f.get("question", "")).strip()
            a = str(f.get("answer", "")).strip()
            if q and a:
                items.append(FAQItem(question=q, answer=a))
    return items
