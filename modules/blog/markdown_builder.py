"""Markdown builder — Phase 7. Assembles final Markdown with rich formatting.

Handles callout boxes, code blocks, tables, lists, blockquotes, and structured elements.
"""

from __future__ import annotations
from typing import Any

from models.blog_generation import BlogResult, BlogSection, BlogSubSection, CalloutBox, FAQItem


def build(blog: BlogResult) -> str:
    """Assemble complete Markdown document from BlogResult."""
    parts: list[str] = []

    if blog.seo_title:
        parts.append(f"# {blog.seo_title}\n")

    if blog.meta_description:
        parts.append(f"> *{blog.meta_description}*\n\n---\n")

    if blog.introduction:
        parts.append(f"{blog.introduction}\n\n---\n")

    if blog.table_of_contents:
        parts.append("## Table of Contents\n")
        for item in blog.table_of_contents:
            parts.append(f"- {item}\n")
        parts.append("\n---\n")

    for section in blog.sections:
        parts.append(_section_md(section))

    if blog.faq:
        parts.append("---\n## Frequently Asked Questions\n")
        for item in blog.faq:
            parts.append(f"### {item.question}\n\n{item.answer}\n\n")

    if blog.conclusion:
        parts.append(f"---\n## Conclusion\n\n{blog.conclusion}\n")

    if blog.call_to_action:
        parts.append(f"---\n\n{blog.call_to_action}\n")

    return "\n".join(parts).strip()


def _section_md(s: BlogSection) -> str:
    parts: list[str] = []
    if s.heading:
        parts.append(f"## {s.heading}\n")
    if s.content:
        parts.append(f"{s.content}\n")
    for b in s.callout_boxes:
        parts.append(_callout(b))
    for sub in s.subsections:
        if sub.heading:
            parts.append(f"### {sub.heading}\n")
        if sub.content:
            parts.append(f"{sub.content}\n")
    return "\n".join(parts)


def _callout(b: CalloutBox) -> str:
    labels = {"tip": "Tip", "warning": "Warning", "note": "Note", "best_practice": "Best Practice"}
    label = labels.get(b.type, "Note")
    return f"> **{label}**\n> {b.text}\n"


def build_code_block(language: str, code: str) -> str:
    return f"```{language}\n{code}\n```"


def build_table(headers: list[str], rows: list[list[str]]) -> str:
    parts: list[str] = []
    parts.append("| " + " | ".join(headers) + " |")
    parts.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        parts.append("| " + " | ".join(row) + " |")
    return "\n".join(parts)
