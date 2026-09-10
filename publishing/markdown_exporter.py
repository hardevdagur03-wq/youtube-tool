from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from publishing.models import (
    DocumentModel, ExportFileInfo, ExportFormat, FORMAT_EXTENSIONS, FORMAT_MIME_TYPES,
)

logger = logging.getLogger(__name__)


class MarkdownExporter:
    def render(self, document: DocumentModel, base_url: str = "") -> str:
        lines: list[str] = []

        lines.append(f"# {document.title}")
        lines.append("")

        meta_lines: list[str] = []
        if document.seo_title and document.seo_title != document.title:
            meta_lines.append(f"> **SEO Title:** {document.seo_title}")
        if document.meta_description:
            meta_lines.append(f"> **Description:** {document.meta_description}")
        if document.author:
            meta_lines.append(f"> **Author:** {document.author}")
        if document.publish_date:
            meta_lines.append(f"> **Published:** {document.publish_date}")
        if document.reading_time_minutes:
            meta_lines.append(f"> **Reading time:** {document.reading_time_minutes} min")
        if document.word_count:
            meta_lines.append(f"> **Word count:** {document.word_count}")
        if meta_lines:
            lines.extend(meta_lines)
            lines.append("")

        metadata_lines: list[str] = []
        if document.category:
            metadata_lines.append(f"| Category | {document.category} |")
        if document.tags:
            metadata_lines.append(f"| Tags | {', '.join(document.tags)} |")
        if document.primary_keyword:
            metadata_lines.append(f"| Primary Keyword | {document.primary_keyword} |")
        if metadata_lines:
            lines.append("## Metadata")
            lines.append("")
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            lines.extend(metadata_lines)
            lines.append("")

        if document.toc:
            lines.append("## Table of Contents")
            lines.append("")
            lines.extend(document.toc)
            lines.append("")

        lines.append("---")
        lines.append("")

        if document.introduction:
            lines.append(document.introduction.strip())
            lines.append("")
            lines.append("---")
            lines.append("")

        for section in document.sections:
            tag = section.heading_tag or "h2"
            prefix = "#" * int(tag[1]) if tag.startswith("h") else "##"
            lines.append(f"{prefix} {section.heading}")
            lines.append("")
            if section.content:
                lines.append(section.content.strip())
                lines.append("")
            for sub in section.subsections:
                sub_prefix = "#" * (int(tag[1]) + 1) if tag.startswith("h") else "###"
                lines.append(f"{sub_prefix} {sub.heading}")
                lines.append("")
                if sub.content:
                    lines.append(sub.content.strip())
                    lines.append("")
            lines.append("---")
            lines.append("")

        if document.faq:
            lines.append("## Frequently Asked Questions")
            lines.append("")
            for faq in document.faq:
                lines.append(f"### {faq.question}")
                lines.append("")
                lines.append(faq.answer)
                lines.append("")
            lines.append("---")
            lines.append("")

        if document.conclusion:
            lines.append(f"## Conclusion")
            lines.append("")
            lines.append(document.conclusion.strip())
            lines.append("")
            lines.append("---")
            lines.append("")

        if document.call_to_action:
            lines.append(f"## {document.call_to_action.split(chr(10))[0] if chr(10) in document.call_to_action else 'Call to Action'}")
            lines.append("")
            lines.append(document.call_to_action.strip())
            lines.append("")
            lines.append("---")
            lines.append("")

        if document.references:
            lines.append("## References")
            lines.append("")
            for ref in document.references:
                lines.append(f"- [{ref.label}]({ref.url})")
            lines.append("")

        return "\n".join(lines)

    def export(self, document: DocumentModel, output_dir: Path, base_url: str = "") -> ExportFileInfo:
        content = self.render(document, base_url)
        filename = f"blog{FORMAT_EXTENSIONS[ExportFormat.MARKDOWN]}"
        filepath = output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        size = filepath.stat().st_size
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
        return ExportFileInfo(
            format=ExportFormat.MARKDOWN,
            filename=filename,
            size_bytes=size,
            size_display=self._size_display(size),
            mime_type=FORMAT_MIME_TYPES[ExportFormat.MARKDOWN],
            checksum=checksum,
        )

    @staticmethod
    def _size_display(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
