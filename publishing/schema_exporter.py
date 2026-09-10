from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from publishing.models import (
    DocumentModel, ExportFileInfo, ExportFormat, FORMAT_EXTENSIONS, FORMAT_MIME_TYPES,
    OpenGraphData, SchemaMarkup, TwitterCardData,
)

logger = logging.getLogger(__name__)


class SchemaExporter:
    def build_schemas(self, document: DocumentModel, base_url: str = "",
                      extra_data: dict[str, Any] | None = None) -> list[SchemaMarkup]:
        schemas: list[SchemaMarkup] = []
        url = base_url.rstrip("/")
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

        article: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": document.seo_title or document.title,
            "description": document.meta_description or "",
            "author": {
                "@type": "Person",
                "name": document.author or "AI Writing Platform",
            },
            "datePublished": document.publish_date or now,
            "dateModified": now,
            "wordCount": document.word_count,
            "articleBody": document.content[:5000] if document.content else "",
        }
        if url:
            article["url"] = url
            article["mainEntityOfPage"] = url
        if document.primary_keyword:
            article["keywords"] = document.primary_keyword
        if document.image_count:
            article["image"] = [img.url for img in document.images[:5]]
        if document.category:
            article["articleSection"] = document.category
        schemas.append(SchemaMarkup(type="Article", data=article))

        breadcrumb: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": url or "https://example.com"},
                {"@type": "ListItem", "position": 2, "name": document.category or "Blog",
                 "item": f"{url}/category/{document.category.lower()}" if url and document.category else ""},
                {"@type": "ListItem", "position": 3, "name": document.title,
                 "item": url or ""},
            ],
        }
        schemas.append(SchemaMarkup(type="BreadcrumbList", data=breadcrumb))

        if document.primary_keyword or document.faq:
            faq_schema: dict[str, Any] = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [],
            }
            for faq in document.faq[:10]:
                faq_schema["mainEntity"].append({
                    "@type": "Question",
                    "name": faq.question,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": faq.answer[:500],
                    },
                })
            if faq_schema["mainEntity"]:
                schemas.append(SchemaMarkup(type="FAQPage", data=faq_schema))

        if extra_data:
            if "organization" in extra_data:
                org: dict[str, Any] = {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": extra_data["organization"].get("name", ""),
                    "url": extra_data["organization"].get("url", url),
                }
                if "logo" in extra_data["organization"]:
                    org["logo"] = extra_data["organization"]["logo"]
                schemas.append(SchemaMarkup(type="Organization", data=org))

            if "person" in extra_data:
                person: dict[str, Any] = {
                    "@context": "https://schema.org",
                    "@type": "Person",
                    "name": extra_data["person"].get("name", document.author),
                }
                if "url" in extra_data["person"]:
                    person["url"] = extra_data["person"]["url"]
                schemas.append(SchemaMarkup(type="Person", data=person))

        return schemas

    def build_opengraph(self, document: DocumentModel, base_url: str = "") -> OpenGraphData:
        return OpenGraphData(
            title=document.seo_title or document.title,
            description=document.meta_description or "",
            type="article",
            url=base_url.rstrip("/"),
            image=document.images[0].url if document.images else "",
            site_name="AI Content Platform",
            locale=f"{document.language}_{document.language.upper()}" if document.language else "en_US",
            published_time=document.publish_date or "",
            author=document.author or "",
        )

    def build_twitter_card(self, document: DocumentModel, base_url: str = "") -> TwitterCardData:
        return TwitterCardData(
            card="summary_large_image",
            title=document.seo_title or document.title,
            description=document.meta_description or "",
            image=document.images[0].url if document.images else "",
            site="@aicontentplatform",
        )

    def export(self, document: DocumentModel, output_dir: Path,
               base_url: str = "", extra_data: dict[str, Any] | None = None) -> list[ExportFileInfo]:
        files: list[ExportFileInfo] = []

        schemas = self.build_schemas(document, base_url, extra_data)
        if schemas:
            all_schema_data = [s.data for s in schemas]
            for i, s in enumerate(schemas):
                content = json.dumps(s.data, indent=2, ensure_ascii=False)
                fname = f"schema_{s.type.lower()}.json"
                fpath = output_dir / fname
                fpath.write_text(content, encoding="utf-8")
                size = fpath.stat().st_size
                files.append(ExportFileInfo(
                    format=ExportFormat.SCHEMA,
                    filename=fname,
                    size_bytes=size,
                    size_display=self._size_display(size),
                    mime_type="application/ld+json",
                    checksum=hashlib.sha256(content.encode("utf-8")).hexdigest()[:32],
                ))

            combined = json.dumps(all_schema_data, indent=2, ensure_ascii=False)
            fpath = output_dir / "schema.json"
            fpath.write_text(combined, encoding="utf-8")
            size = fpath.stat().st_size
            files.append(ExportFileInfo(
                format=ExportFormat.SCHEMA,
                filename="schema.json",
                size_bytes=size,
                mime_type="application/ld+json",
                checksum=hashlib.sha256(combined.encode("utf-8")).hexdigest()[:32],
            ))

        og = self.build_opengraph(document, base_url)
        og_content = og.model_dump_json(indent=2)
        fpath = output_dir / "opengraph.json"
        fpath.write_text(og_content, encoding="utf-8")
        size = fpath.stat().st_size
        files.append(ExportFileInfo(
            format=ExportFormat.SCHEMA,
            filename="opengraph.json",
            size_bytes=size,
            mime_type="application/json",
            checksum=hashlib.sha256(og_content.encode("utf-8")).hexdigest()[:32],
        ))

        twitter = self.build_twitter_card(document, base_url)
        tw_content = twitter.model_dump_json(indent=2)
        fpath = output_dir / "twitter_card.json"
        fpath.write_text(tw_content, encoding="utf-8")
        size = fpath.stat().st_size
        files.append(ExportFileInfo(
            format=ExportFormat.SCHEMA,
            filename="twitter_card.json",
            size_bytes=size,
            mime_type="application/json",
            checksum=hashlib.sha256(tw_content.encode("utf-8")).hexdigest()[:32],
        ))

        return files

    @staticmethod
    def _size_display(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
