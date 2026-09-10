"""Link recommender — Phase 8. Generates contextual internal/external link suggestions."""

from __future__ import annotations
import re
from typing import Any

from models.blog_generation import BlogResult


_AUTHORITY_DOMAINS = {
    "python": "https://docs.python.org/3/",
    "javascript": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "typescript": "https://www.typescriptlang.org/docs/",
    "react": "https://react.dev/",
    "node": "https://nodejs.org/docs/",
    "docker": "https://docs.docker.com/",
    "kubernetes": "https://kubernetes.io/docs/",
    "aws": "https://aws.amazon.com/documentation/",
    "google cloud": "https://cloud.google.com/docs",
    "azure": "https://learn.microsoft.com/en-us/azure/",
    "tensorflow": "https://www.tensorflow.org/api_docs",
    "pytorch": "https://pytorch.org/docs/",
    "machine learning": "https://developers.google.com/machine-learning/",
    "w3c": "https://www.w3.org/TR/",
    "mdn": "https://developer.mozilla.org/",
    "wikipedia": "https://en.wikipedia.org/wiki/",
}


def suggest_internal(blog: BlogResult) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    seen = set()
    for s in blog.sections:
        words = s.heading.lower().split()
        for w in words:
            if len(w) > 4 and w not in seen:
                seen.add(w)
                links.append({
                    "anchor_text": s.heading[:40] or w,
                    "suggested_topic": s.heading or w,
                    "suggested_url": "",
                    "relevance_score": round(0.7 + (len(s.heading) / 200) * 0.3, 2),
                })
                break
    return links[:8]


def suggest_external(blog: BlogResult) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    seen_topics = set()
    full = " ".join([blog.seo_title, blog.introduction] + [s.content for s in blog.sections] + [blog.conclusion]).lower()

    for topic, url in _AUTHORITY_DOMAINS.items():
        if topic in full and topic not in seen_topics:
            seen_topics.add(topic)
            links.append({
                "anchor_text": f"Official {topic.title()} Documentation",
                "suggested_topic": topic,
                "suggested_url": url,
                "relevance_score": 0.9,
            })

    return links[:5]
