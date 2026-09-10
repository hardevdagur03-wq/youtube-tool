from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from publishing.models import (
    DocumentModel, ExportFileInfo, ExportFormat, FORMAT_EXTENSIONS, FORMAT_MIME_TYPES,
)

logger = logging.getLogger(__name__)


class JSONExporter:
    def render(self, document: DocumentModel, extra: dict[str, Any] | None = None) -> str:
        data: dict[str, Any] = {
            "title": document.title,
            "seo_title": document.seo_title,
            "meta_description": document.meta_description,
            "author": document.author,
            "publish_date": document.publish_date,
            "language": document.language,
            "word_count": document.word_count,
            "reading_time_minutes": document.reading_time_minutes,
            "category": document.category,
            "tags": document.tags,
            "primary_keyword": document.primary_keyword,
            "secondary_keywords": document.secondary_keywords,
            "content": document.content,
            "sections": [
                {
                    "heading": s.heading,
                    "heading_tag": s.heading_tag,
                    "content": s.content,
                    "subsections": [
                        {"heading": sub.heading, "content": sub.content}
                        for sub in s.subsections
                    ],
                    "order": s.order,
                    "word_count": s.word_count,
                }
                for s in document.sections
            ],
            "headings": [
                {"text": h.text, "tag": h.tag, "level": h.level}
                for h in document.headings
            ],
            "faq": [
                {"question": f.question, "answer": f.answer}
                for f in document.faq
            ],
            "images": [
                {"url": img.url, "alt": img.alt, "caption": img.caption, "filename": img.filename}
                for img in document.images
            ],
            "tables": [
                {
                    "headers": t.headers,
                    "rows": t.rows,
                    "caption": t.caption,
                    "alignment": t.alignment,
                }
                for t in document.tables
            ],
            "code_blocks": [
                {"language": cb.language, "code": cb.code, "caption": cb.caption}
                for cb in document.code_blocks
            ],
            "links": [
                {"text": l.text, "url": l.url, "is_internal": l.is_internal}
                for l in document.links
            ],
            "references": [
                {"label": r.label, "url": r.url}
                for r in document.references
            ],
            "introduction": document.introduction,
            "conclusion": document.conclusion,
            "call_to_action": document.call_to_action,
        }

        if extra:
            data.update(extra)

        return json.dumps(data, indent=2, ensure_ascii=False)

    def export(self, document: DocumentModel, output_dir: Path,
               extra: dict[str, Any] | None = None, base_url: str = "") -> ExportFileInfo:
        content = self.render(document, extra)
        filename = f"blog{FORMAT_EXTENSIONS[ExportFormat.JSON]}"
        filepath = output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        size = filepath.stat().st_size
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
        return ExportFileInfo(
            format=ExportFormat.JSON,
            filename=filename,
            size_bytes=size,
            size_display=self._size_display(size),
            mime_type=FORMAT_MIME_TYPES[ExportFormat.JSON],
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
