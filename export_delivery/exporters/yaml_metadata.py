"""YAML Metadata Exporter — generates a standalone metadata file.

Produces a YAML file with title, description, author, dates, tags,
SEO score, word count, reading time, and export version.
Compatible with Jekyll, Hugo, and static site generators.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from export_delivery.models import TemplateConfig

logger = logging.getLogger(__name__)


class YAMLMetadataExporter:
    """Generates YAML metadata files compatible with static site generators.

    Outputs: metadata.yaml with full document metadata for CMS integration.
    """

    def export(
        self,
        document: Any,
        output_dir: str = "",
        template_config: TemplateConfig | None = None,
    ) -> dict[str, Any]:
        """Export metadata as YAML.

        Args:
            document: Document-like object.
            output_dir: Output directory.
            template_config: Unused for metadata.

        Returns:
            Dict with file info.
        """
        output_dir = output_dir or os.path.join(
            os.getcwd(), "exports_delivery", getattr(document, "project_id", "unknown")
        )
        os.makedirs(output_dir, exist_ok=True)

        metadata = self._build_metadata(document)
        slug = getattr(document, "slug", "") or self._slugify(getattr(document, "title", "export"))
        filename = f"{slug}-metadata.yaml"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self._to_yaml(metadata))

        size = os.path.getsize(filepath)
        logger.info("YAML metadata exported: %s (%d bytes)", filename, size)

        return {
            "format": "yaml_metadata",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "mime_type": "text/yaml",
        }

    def _build_metadata(self, document: Any) -> dict[str, Any]:
        """Build structured metadata from document."""
        title = getattr(document, "title", "")
        content = getattr(document, "content", "") or ""
        word_count = getattr(document, "word_count", 0) or len(content.split())
        tags = getattr(document, "tags", []) or []
        sections = getattr(document, "sections", []) or []

        return {
            "title": title,
            "description": getattr(document, "meta_description", ""),
            "author": getattr(document, "author", ""),
            "date": getattr(document, "publish_date", "") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "slug": getattr(document, "slug", "") or self._slugify(title),
            "category": getattr(document, "category", ""),
            "tags": tags if isinstance(tags, list) else [tags],
            "language": getattr(document, "language", "en"),
            "word_count": word_count,
            "reading_time_minutes": getattr(document, "reading_time", 0) or max(1, word_count // 200),
            "seo_score": getattr(document, "seo_score", 0),
            "export_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": "article",
            "section_count": len(sections),
            "image_count": len(getattr(document, "images", []) or []),
            "faq_count": len(getattr(document, "faq", []) or []),
            "reference_count": len(getattr(document, "references", []) or []),
        }

    @staticmethod
    def _to_yaml(data: dict, indent: int = 0) -> str:
        """Convert dict to YAML string manually (no PyYAML dependency)."""
        lines = []
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(YAMLMetadataExporter._to_yaml(value, indent + 1))
            elif isinstance(value, list):
                if not value:
                    lines.append(f"{prefix}{key}: []")
                else:
                    lines.append(f"{prefix}{key}:")
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(f"{prefix}  -")
                            lines.append(YAMLMetadataExporter._to_yaml(item, indent + 2))
                        else:
                            lines.append(f'{prefix}  - "{item}"')
            elif isinstance(value, bool):
                lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
            elif isinstance(value, int):
                lines.append(f"{prefix}{key}: {value}")
            elif isinstance(value, float):
                lines.append(f"{prefix}{key}: {value}")
            else:
                val = str(value).strip()
                if ":" in val or any(c in val for c in "#{}[]"):
                    lines.append(f'{prefix}{key}: "{val}"')
                else:
                    lines.append(f"{prefix}{key}: {val}")
        return "\n".join(lines)

    @staticmethod
    def _slugify(text: str) -> str:
        if not text:
            return "untitled"
        slug = text.lower().strip().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug.strip("-") or "untitled"
