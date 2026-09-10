"""Final markdown assembly â€” combines all blog components into a polished document.

Assembles: title, introduction, table of contents, sections, FAQ, conclusion, CTA.
"""

from __future__ import annotations
from typing import Any

from models.blog_generation import BlogResult, BlogSection


def assemble_blog(blog: BlogResult) -> str:
    """Assemble all blog components into a single Markdown document.

    Args:
        blog: Fully populated BlogResult.

    Returns:
        Complete Markdown string ready for publication.
    """
    parts: list[str] = []

    has_header = bool(blog.seo_title or blog.introduction)

    # Title
    if blog.seo_title:
        parts.append(f"# {blog.seo_title}\n")

    # Introduction
    if blog.introduction:
        parts.append(f"{blog.introduction}\n")

    # Horizontal rule after header
    if has_header:
        parts.append("---\n")

    # Table of contents
    if blog.table_of_contents:
        parts.append("## Table of Contents\n")
        for item in blog.table_of_contents:
            parts.append(f"- {item}\n")
        parts.append("\n---\n")

    # Sections
    for section in blog.sections:
        if section.heading:
            parts.append(f"## {section.heading}\n")
        if section.content:
            parts.append(f"{section.content}\n")
        for sub in section.subsections:
            if sub.heading:
                parts.append(f"### {sub.heading}\n")
            if sub.content:
                parts.append(f"{sub.content}\n")

    # FAQ
    if blog.faq:
        parts.append("---\n")
        parts.append("## Frequently Asked Questions\n")
        for faq_item in blog.faq:
            parts.append(f"### {faq_item.question}\n")
            parts.append(f"{faq_item.answer}\n")

    # Conclusion
    if blog.conclusion:
        parts.append("---\n")
        parts.append("## Conclusion\n")
        parts.append(f"{blog.conclusion}\n")

    # CTA
    if blog.call_to_action:
        parts.append("---\n")
        parts.append(f"{blog.call_to_action}\n")

    return "\n".join(parts).strip()


def assemble_full_response(blog: BlogResult, full_markdown: str) -> dict[str, Any]:
    """Assemble the full API response dict with blog + markdown."""
    return {
        "blog": {
            "title": blog.seo_title,
            "introduction": blog.introduction,
            "table_of_contents": blog.table_of_contents,
            "sections": [
                {
                    "heading": s.heading,
                    "content": s.content,
                    "subsections": [
                        {"heading": sub.heading, "content": sub.content}
                        for sub in s.subsections
                    ],
                }
                for s in blog.sections
            ],
            "faq": [
                {"question": f.question, "answer": f.answer}
                for f in blog.faq
            ],
            "conclusion": blog.conclusion,
            "cta": blog.call_to_action,
            "metadata": {"seo_title": blog.seo_title, "meta_description": blog.meta_description, "slug": blog.slug, "statistics": blog.statistics.model_dump()},
            "markdown": full_markdown,
        },
    }

