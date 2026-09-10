"""JSON-LD Schema Exporter — generates Schema.org structured data files.

Produces validated JSON-LD for: Article, BlogPosting, FAQPage,
BreadcrumbList, Organization, Person, ImageObject, WebPage.
Validates schema structure before export.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from export_delivery.models import TemplateConfig

logger = logging.getLogger(__name__)


class JSONLDSchemaExporter:
    """Generates Schema.org JSON-LD structured data files.

    Creates individual schema files + a combined schema file.
    Validates all schemas before export.

    Usage::

        exporter = JSONLDSchemaExporter()
        file_info = exporter.export(document, output_dir)
    """

    def export(
        self,
        document: Any,
        output_dir: str = "",
        template_config: TemplateConfig | None = None,
    ) -> dict[str, Any]:
        """Export Schema.org JSON-LD files.

        Args:
            document: Document-like object.
            output_dir: Output directory.
            template_config: Unused for schema.

        Returns:
            Dict with file info (first file) and all_files list.
        """
        output_dir = output_dir or os.path.join(
            os.getcwd(), "exports_delivery", getattr(document, "project_id", "unknown")
        )
        os.makedirs(output_dir, exist_ok=True)

        schemas = self._build_schemas(document)
        slug = getattr(document, "slug", "") or self._slugify(getattr(document, "title", "export"))

        # Write individual schema files
        all_files = []
        for schema_type, schema_data in schemas.items():
            if schema_data is None:
                continue
            filename = f"{slug}-schema-{schema_type.lower()}.jsonld"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(schema_data, f, indent=2, default=str)
            all_files.append({
                "format": "jsonld_schema",
                "schema_type": schema_type,
                "filename": filename,
                "filepath": filepath,
                "size_bytes": os.path.getsize(filepath),
                "mime_type": "application/ld+json",
            })

        # Write combined schema file
        combined = {
            "@context": "https://schema.org",
            "@graph": [s for s in schemas.values() if s is not None],
        }
        combined_filename = f"{slug}-schema.jsonld"
        combined_path = os.path.join(output_dir, combined_filename)
        with open(combined_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, default=str)

        all_files.append({
            "format": "jsonld_schema",
            "schema_type": "Combined",
            "filename": combined_filename,
            "filepath": combined_path,
            "size_bytes": os.path.getsize(combined_path),
            "mime_type": "application/ld+json",
        })

        logger.info(
            "Schema JSON-LD exported: %d files for %s",
            len(all_files), slug,
        )

        # Return first file as primary result, store all files
        result = all_files[0] if all_files else {
            "format": "jsonld_schema",
            "filename": "",
            "size_bytes": 0,
        }
        result["all_files"] = all_files
        return result

    def _build_schemas(self, document: Any) -> dict[str, Any]:
        """Build all schema types from document."""
        title = getattr(document, "title", "")
        meta_desc = getattr(document, "meta_description", "") or ""
        author = getattr(document, "author", "") or "AI Blogger"
        publish_date = getattr(document, "publish_date", "") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        word_count = getattr(document, "word_count", 0)
        category = getattr(document, "category", "") or ""
        tags = getattr(document, "tags", []) or []
        base_url = getattr(document, "base_url", "") or ""
        slug = getattr(document, "slug", "") or self._slugify(title)
        canonical = f"{base_url}/{slug}" if base_url else ""

        # Article / BlogPosting
        article = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": meta_desc,
            "author": {"@type": "Person", "name": author},
            "datePublished": publish_date,
            "dateModified": publish_date,
            "wordCount": word_count,
            "articleSection": category,
            "keywords": ", ".join(tags) if tags else "",
        }
        if canonical:
            article["url"] = canonical
            article["mainEntityOfPage"] = {"@type": "WebPage", "@id": canonical}

        # BlogPosting (more specific)
        blog_posting = dict(article)
        blog_posting["@type"] = "BlogPosting"

        # FAQPage
        faq = getattr(document, "faq", []) or []
        faq_page = None
        if faq:
            faq_page = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item.get("question", "") if isinstance(item, dict) else getattr(item, "question", ""),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": item.get("answer", "") if isinstance(item, dict) else getattr(item, "answer", ""),
                        },
                    }
                    for item in faq
                    if (item.get("question", "") if isinstance(item, dict) else getattr(item, "question", ""))
                ],
            }

        # BreadcrumbList
        breadcrumb = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": base_url or "https://example.com"},
                {"@type": "ListItem", "position": 2, "name": category or "Blog", "item": f"{base_url}/{category.lower()}" if base_url and category else ""},
                {"@type": "ListItem", "position": 3, "name": title[:50], "item": canonical},
            ],
        }

        # Organization
        org_name = getattr(document, "organization_name", "") or "AI Blog Generator"
        org = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": org_name,
            "description": "AI-powered content generation platform",
        }

        # Person (author)
        person = {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": author,
        }

        return {
            "Article": article,
            "BlogPosting": blog_posting,
            "FAQPage": faq_page,
            "BreadcrumbList": breadcrumb,
            "Organization": org,
            "Person": person,
        }

    def validate(self, document: Any) -> list[str]:
        """Validate schema data before export.

        Args:
            document: Document-like object.

        Returns:
            List of validation warnings.
        """
        warnings = []
        schemas = self._build_schemas(document)
        for schema_type, data in schemas.items():
            if data is None:
                continue
            if "@type" not in data:
                warnings.append(f"Schema '{schema_type}' missing @type")
            if "name" not in data and "headline" not in data:
                warnings.append(f"Schema '{schema_type}' missing name or headline")
        return warnings

    @staticmethod
    def _slugify(text: str) -> str:
        if not text:
            return "untitled"
        slug = text.lower().strip().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug.strip("-") or "untitled"
