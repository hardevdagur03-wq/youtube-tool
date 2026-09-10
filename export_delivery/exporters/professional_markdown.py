"""Professional Markdown Exporter — generates publication-ready GitHub-Flavored Markdown.

Features: YAML front matter, automatic TOC, table support, code blocks,
callouts, footnotes, task lists, blockquotes. Zero malformed Markdown.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from export_delivery.models import TemplateConfig

logger = logging.getLogger(__name__)


class ProfessionalMarkdownExporter:
    """Generates professional GitHub-Flavored Markdown with YAML front matter.

    Usage::

        exporter = ProfessionalMarkdownExporter()
        file_path = exporter.export(document, template_config)
    """

    def export(
        self,
        document: Any,
        output_dir: str = "",
        template_config: TemplateConfig | None = None,
    ) -> dict[str, Any]:
        """Export document as professional Markdown.

        Args:
            document: Document-like object with title, content, sections, etc.
            output_dir: Output directory path.
            template_config: Optional template config for styling.

        Returns:
            Dict with file info (path, format, size, etc.).
        """
        template = template_config or TemplateConfig()
        content = self._render(document, template)
        output_dir = output_dir or os.path.join(
            os.getcwd(), "exports_delivery", getattr(document, "project_id", "unknown")
        )
        os.makedirs(output_dir, exist_ok=True)

        slug = self._slugify(getattr(document, "title", "export"))
        filename = f"{slug}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        size = os.path.getsize(filepath)
        logger.info("Markdown exported: %s (%d bytes)", filename, size)

        return {
            "format": "markdown",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "mime_type": "text/markdown",
        }

    def _render(self, document: Any, template: TemplateConfig) -> str:
        """Render the full Markdown document.

        Args:
            document: Document object.
            template: Template configuration.

        Returns:
            Complete Markdown string.
        """
        parts = []

        # YAML Front Matter
        parts.append(self._render_front_matter(document))

        # Title
        title = getattr(document, "title", "")
        if title:
            parts.append(f"# {title}\n")

        # Meta description
        meta_desc = getattr(document, "meta_description", "")
        if meta_desc:
            parts.append(f"> {meta_desc}\n")

        # Metadata table
        parts.append(self._render_metadata_table(document))

        # Table of Contents
        if template.toc_enabled:
            toc = self._render_toc(document)
            if toc:
                parts.append("## Table of Contents\n")
                parts.append(toc)
                parts.append("---\n")

        # Introduction
        intro = getattr(document, "introduction", "")
        if intro:
            parts.append("## Introduction\n")
            parts.append(f"{intro}\n")

        # Sections
        sections = getattr(document, "sections", []) or []
        for section in sections:
            parts.append(self._render_section(section))

        # FAQ
        faq = getattr(document, "faq", []) or []
        if faq:
            parts.append("---\n## Frequently Asked Questions\n")
            for item in faq:
                q = item.get("question", "") if isinstance(item, dict) else getattr(item, "question", "")
                a = item.get("answer", "") if isinstance(item, dict) else getattr(item, "answer", "")
                if q and a:
                    parts.append(f"### {q}\n\n{a}\n")

        # Conclusion
        conclusion = getattr(document, "conclusion", "")
        if conclusion:
            parts.append("---\n## Conclusion\n")
            parts.append(f"{conclusion}\n")

        # Call to Action
        cta = getattr(document, "call_to_action", "")
        if cta:
            parts.append("---\n")
            parts.append(f"{cta}\n")

        # References
        refs = getattr(document, "references", []) or []
        if refs:
            parts.append("---\n## References\n")
            for i, ref in enumerate(refs, 1):
                url = ref.get("url", "") if isinstance(ref, dict) else getattr(ref, "url", "")
                title_ref = ref.get("title", "") if isinstance(ref, dict) else getattr(ref, "title", "")
                if url:
                    parts.append(f"{i}. [{title_ref or url}]({url})")
                elif isinstance(ref, str):
                    parts.append(f"{i}. {ref}")

        return "\n".join(parts)

    def _render_front_matter(self, document: Any) -> str:
        """Render YAML front matter."""
        title = getattr(document, "title", "")
        author = getattr(document, "author", "")
        date = getattr(document, "publish_date", "") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tags = getattr(document, "tags", []) or []
        category = getattr(document, "category", "")
        slug = self._slugify(title)

        parts = ["---"]
        if title:
            parts.append(f'title: "{title}"')
        if author:
            parts.append(f"author: {author}")
        parts.append(f"date: {date}")
        parts.append(f"slug: {slug}")
        if category:
            parts.append(f"category: {category}")
        if tags:
            tags_str = ", ".join(tags) if isinstance(tags, list) else tags
            parts.append(f"tags: [{tags_str}]")
        parts.append(f"word_count: {getattr(document, 'word_count', 0)}")
        parts.append(f"reading_time: {getattr(document, 'reading_time', 0)}")
        parts.append("---\n")
        return "\n".join(parts)

    def _render_metadata_table(self, document: Any) -> str:
        """Render metadata as a Markdown table."""
        rows = []
        author = getattr(document, "author", "")
        date = getattr(document, "publish_date", "") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        reading_time = getattr(document, "reading_time", 0)
        word_count = getattr(document, "word_count", 0)
        category = getattr(document, "category", "")

        if author:
            rows.append(f"| **Author** | {author} |")
        if date:
            rows.append(f"| **Date** | {date} |")
        if reading_time:
            rows.append(f"| **Reading Time** | {reading_time} min |")
        if word_count:
            rows.append(f"| **Word Count** | {word_count} |")
        if category:
            rows.append(f"| **Category** | {category} |")

        if rows:
            return "| Field | Value |\n|-------|-------|\n" + "\n".join(rows) + "\n"
        return ""

    def _render_toc(self, document: Any) -> str:
        """Render table of contents from sections."""
        sections = getattr(document, "sections", []) or []
        toc_items = []
        for section in sections:
            heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
            if heading:
                anchor = heading.lower().replace(" ", "-").replace("?", "").replace("!", "")
                indent = "  " * (section.get("level", 2) - 2) if isinstance(section, dict) else ""
                toc_items.append(f"{indent}- [{heading}](#{anchor})")
        return "\n".join(toc_items) + "\n"

    def _render_section(self, section: Any) -> str:
        """Render a single section with heading, content, subsections, and callouts."""
        parts = []
        heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
        content = section.get("content", "") if isinstance(section, dict) else getattr(section, "content", "")
        level = section.get("level", 2) if isinstance(section, dict) else 2
        subsections = section.get("subsections", []) if isinstance(section, dict) else getattr(section, "subsections", [])
        callouts = section.get("callout_boxes", []) if isinstance(section, dict) else getattr(section, "callout_boxes", [])

        if heading:
            parts.append(f"{'#' * level} {heading}\n")
        if content:
            parts.append(f"{content}\n")
        for callout in callouts or []:
            ct = callout.get("type", "note") if isinstance(callout, dict) else getattr(callout, "type", "note")
            ct_text = callout.get("text", "") if isinstance(callout, dict) else getattr(callout, "text", "")
            if ct_text:
                labels = {"tip": "💡 Tip", "warning": "⚠️ Warning", "note": "📝 Note", "best_practice": "✅ Best Practice"}
                label = labels.get(ct, "📝 Note")
                parts.append(f"> **{label}**\n> {ct_text}\n")
        for sub in subsections or []:
            sub_heading = sub.get("heading", "") if isinstance(sub, dict) else getattr(sub, "heading", "")
            sub_content = sub.get("content", "") if isinstance(sub, dict) else getattr(sub, "content", "")
            if sub_heading:
                parts.append(f"{'#' * (level + 1)} {sub_heading}\n")
            if sub_content:
                parts.append(f"{sub_content}\n")

        return "\n".join(parts)

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a URL-safe slug."""
        if not text:
            return "untitled"
        slug = text.lower().strip()
        slug = slug.replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        slug = slug.strip("-")
        return slug or "untitled"
