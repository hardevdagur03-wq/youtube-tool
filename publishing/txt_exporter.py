from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from publishing.models import (
    DocumentModel, ExportFileInfo, ExportFormat, FORMAT_EXTENSIONS, FORMAT_MIME_TYPES,
)

logger = logging.getLogger(__name__)


class TxtExporter:
    def render(self, document: DocumentModel) -> str:
        lines: list[str] = []

        lines.append(document.seo_title or document.title)
        lines.append("=" * len(document.seo_title or document.title))
        lines.append("")

        if document.author or document.publish_date:
            parts = []
            if document.author:
                parts.append(f"Author: {document.author}")
            if document.publish_date:
                parts.append(f"Published: {document.publish_date}")
            if document.reading_time_minutes:
                parts.append(f"Reading Time: {document.reading_time_minutes} min")
            if document.word_count:
                parts.append(f"Words: {document.word_count}")
            lines.append(" | ".join(parts))
            lines.append("")

        if document.meta_description:
            lines.append(document.meta_description)
            lines.append("")

        if document.category or document.tags:
            parts = []
            if document.category:
                parts.append(f"Category: {document.category}")
            if document.tags:
                parts.append(f"Tags: {', '.join(document.tags)}")
            lines.append(" | ".join(parts))
            lines.append("")

        lines.append("-" * 60)
        lines.append("")

        if document.introduction:
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", document.introduction)
            text = re.sub(r"\*(.+?)\*", r"\1", text)
            text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
            lines.append(text)
            lines.append("")
            lines.append("-" * 60)
            lines.append("")

        for section in document.sections:
            tag = section.heading_tag or "h2"
            level = int(tag[1]) if tag.startswith("h") else 2
            prefix = "#" * level
            lines.append(f"{prefix} {section.heading}")
            lines.append("")
            if section.content:
                text = re.sub(r"\*\*(.+?)\*\*", r"\1", section.content)
                text = re.sub(r"\*(.+?)\*", r"\1", text)
                text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
                lines.append(text)
                lines.append("")
            for sub in section.subsections:
                sub_prefix = "#" * (int(tag[1]) + 1)
                lines.append(f"{sub_prefix} {sub.heading}")
                lines.append("")
                if sub.content:
                    text = re.sub(r"\*\*(.+?)\*\*", r"\1", sub.content)
                    text = re.sub(r"\*(.+?)\*", r"\1", text)
                    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
                    lines.append(text)
                    lines.append("")
            lines.append("-" * 60)
            lines.append("")

        if document.faq:
            lines.append("FREQUENTLY ASKED QUESTIONS")
            lines.append("=" * 30)
            lines.append("")
            for faq in document.faq:
                text = re.sub(r"\*\*(.+?)\*\*", r"\1", faq.question)
                text = re.sub(r"\*(.+?)\*", r"\1", text)
                lines.append(f"Q: {text}")
                text = re.sub(r"\*\*(.+?)\*\*", r"\1", faq.answer)
                text = re.sub(r"\*(.+?)\*", r"\1", text)
                lines.append(f"A: {text}")
                lines.append("")
            lines.append("-" * 60)
            lines.append("")

        if document.conclusion:
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", document.conclusion)
            text = re.sub(r"\*(.+?)\*", r"\1", text)
            lines.append("CONCLUSION")
            lines.append("=" * 30)
            lines.append("")
            lines.append(text)
            lines.append("")

        if document.call_to_action:
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", document.call_to_action)
            text = re.sub(r"\*(.+?)\*", r"\1", text)
            lines.append("")
            lines.append(text)

        if document.references:
            lines.append("")
            lines.append("REFERENCES")
            lines.append("=" * 30)
            lines.append("")
            for ref in document.references:
                lines.append(f"- {ref.label}: {ref.url}")

        return "\n".join(lines)

    def export(self, document: DocumentModel, output_dir: Path, base_url: str = "") -> ExportFileInfo:
        content = self.render(document)
        filename = f"blog{FORMAT_EXTENSIONS[ExportFormat.TXT]}"
        filepath = output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        size = filepath.stat().st_size
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
        return ExportFileInfo(
            format=ExportFormat.TXT,
            filename=filename,
            size_bytes=size,
            size_display=self._size_display(size),
            mime_type=FORMAT_MIME_TYPES[ExportFormat.TXT],
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
