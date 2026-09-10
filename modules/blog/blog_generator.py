"""Blog generation logic — separates generation from orchestration.

This module handles the actual LLM interaction for blog content.
BlogService orchestrates; BlogGenerator generates.
"""

from __future__ import annotations
import logging
from typing import Any

from modules.ai.provider import LLMProvider, LLMResponse
from modules.ai.prompt_builder import build_blog_prompt, get
from modules.ai.response_parser import to_blog_model
from models.blog_generation import BlogResult, BlogSection, BlogSubSection, CalloutBox, FAQItem, BlogStatistics
from exceptions.blog_errors import BlogGenerationError

logger = logging.getLogger(__name__)


def generate_blog(
    provider: LLMProvider,
    transcript: str,
    metadata: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
) -> BlogResult:
    """Generate full blog via LLM, return parsed BlogResult."""
    system = get("system.md")
    prompt = build_blog_prompt(transcript, metadata, analysis)
    raw = provider.generate_json(prompt, system)
    blog = to_blog_model(raw)
    return blog


def generate_full_markdown(blog: BlogResult) -> str:
    """Assemble complete Markdown from a BlogResult."""
    parts: list[str] = []

    if blog.seo_title:
        parts.append(f"# {blog.seo_title}\n")

    if blog.meta_description:
        parts.append(f"> {blog.meta_description}\n")

    if blog.introduction:
        parts.append(f"{blog.introduction}\n")

    if blog.table_of_contents:
        parts.append("## Table of Contents\n")
        for item in blog.table_of_contents:
            parts.append(f"- {item}\n")
        parts.append("\n---\n")

    for section in blog.sections:
        if section.heading:
            parts.append(f"## {section.heading}\n")
        if section.content:
            parts.append(f"{section.content}\n")
        for box in section.callout_boxes:
            parts.append(_callout_md(box.type, box.text))
        for sub in section.subsections:
            if sub.heading:
                parts.append(f"### {sub.heading}\n")
            if sub.content:
                parts.append(f"{sub.content}\n")

    if blog.faq:
        parts.append("---\n## Frequently Asked Questions\n")
        for item in blog.faq:
            parts.append(f"### {item.question}\n{item.answer}\n")

    if blog.conclusion:
        parts.append(f"---\n## Conclusion\n{blog.conclusion}\n")

    if blog.call_to_action:
        parts.append(f"---\n{blog.call_to_action}\n")

    return "\n".join(parts).strip()


def _callout_md(typ: str, text: str) -> str:
    labels = {"tip": "💡 Tip", "warning": "⚠️ Warning", "note": "📝 Note", "best_practice": "✅ Best Practice"}
    label = labels.get(typ, "📝 Note")
    return f"> **{label}**\n> {text}\n"
