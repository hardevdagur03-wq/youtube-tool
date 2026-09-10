"""Markdown Exporter — Phase 10.

Generates clean GitHub-compatible Markdown with proper heading hierarchy,
tables, code fences, links, images, blockquotes, FAQs, and TOC.
"""

from __future__ import annotations
from pathlib import Path

from models.blog_export import ExportRequest, ExportFile
from export.base import BaseExporter


class MarkdownExporter(BaseExporter):
    """Exports blog to GitHub-compatible Markdown."""

    def format_name(self) -> str:
        return "markdown"

    def file_extension(self) -> str:
        return ".md"

    def mime_type(self) -> str:
        return "text/markdown"

    def export(self, request: ExportRequest, output_dir: Path) -> ExportFile:
        lines: list[str] = []
        filename = f"{self.sanitize_filename(request.blog_title)}{self.file_extension()}"
        filepath = output_dir / filename

        # Title
        if request.blog_title:
            lines.append(f"# {request.blog_title}\n")

        # Meta
        meta_lines = []
        if request.meta_description:
            meta_lines.append(f"> *{request.meta_description}*")
        if request.author:
            meta_lines.append(f"> **Author:** {request.author}")
        if request.publish_date:
            meta_lines.append(f"> **Published:** {request.publish_date}")
        if request.reading_time:
            meta_lines.append(f"> **Reading time:** {request.reading_time}")
        if request.word_count:
            meta_lines.append(f"> **Word count:** {request.word_count:,}")
        if meta_lines:
            lines.extend(meta_lines)
            lines.append("")
            lines.append("---\n")

        # Metadata table
        lines.append("## Metadata\n")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        if request.category:
            lines.append(f"| Category | {request.category} |")
        if request.tags:
            lines.append(f"| Tags | {', '.join(request.tags)} |")
        if request.primary_keyword:
            lines.append(f"| Primary Keyword | {request.primary_keyword} |")
        if request.secondary_keywords:
            lines.append(f"| Secondary Keywords | {', '.join(request.secondary_keywords)} |")
        lines.append("")

        # Table of Contents
        if request.table_of_contents:
            lines.append("## Table of Contents\n")
            for item in request.table_of_contents:
                slug = item.lower().replace(' ', '-').replace('/', '').replace('?', '')
                slug = ''.join(c for c in slug if c.isalnum() or c == '-')
                lines.append(f"- [{item}](#{slug})")
            lines.append("")
            lines.append("---\n")

        # Introduction
        if request.introduction:
            lines.append(f"{request.introduction}\n")

        # Sections
        for section in request.sections:
            heading = section.get("heading", "")
            content = section.get("content", "")
            subsections = section.get("subsections", [])

            if heading:
                lines.append(f"## {heading}\n")
            if content:
                lines.append(f"{content}\n")

            for sub in subsections:
                sub_heading = sub.get("heading", "")
                sub_content = sub.get("content", "")
                if sub_heading:
                    lines.append(f"### {sub_heading}\n")
                if sub_content:
                    lines.append(f"{sub_content}\n")

        # FAQ
        if request.faq:
            lines.append("---\n")
            lines.append("## Frequently Asked Questions\n")
            for faq in request.faq:
                q = faq.get("question", "")
                a = faq.get("answer", "")
                if q:
                    lines.append(f"### {q}\n")
                if a:
                    lines.append(f"{a}\n")

        # Conclusion
        if request.conclusion:
            lines.append("---\n")
            lines.append("## Conclusion\n")
            lines.append(f"{request.conclusion}\n")

        # CTA
        if request.call_to_action:
            lines.append("---\n")
            lines.append(f"{request.call_to_action}\n")

        # References
        if request.references:
            lines.append("---\n")
            lines.append("## References\n")
            for ref in request.references:
                label = ref.get("label", "")
                url = ref.get("url", "")
                if label and url:
                    lines.append(f"- [{label}]({url})")
                elif url:
                    lines.append(f"- {url}")
                elif label:
                    lines.append(f"- {label}")

        content = "\n".join(lines).strip()
        filepath.write_text(content, encoding="utf-8")

        size = filepath.stat().st_size
        return ExportFile(
            format=self.format_name(),
            filename=filename,
            size_bytes=size,
            size_display=self._size_display(size),
            download_url=f"/api/export/download/{filename}",
            mime_type=self.mime_type(),
        )
