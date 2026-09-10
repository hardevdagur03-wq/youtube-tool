"""HTML Exporter — Phase 10.

Generates semantic HTML5 with responsive layout, SEO meta tags,
Open Graph, Twitter Cards, JSON-LD Schema, and accessibility.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime, timezone

from models.blog_export import ExportRequest, ExportFile
from export.base import BaseExporter


class HTMLExporter(BaseExporter):
    """Exports blog to semantic HTML5 with full SEO metadata."""

    def format_name(self) -> str:
        return "html"

    def file_extension(self) -> str:
        return ".html"

    def mime_type(self) -> str:
        return "text/html"

    def export(self, request: ExportRequest, output_dir: Path) -> ExportFile:
        filename = f"{self.sanitize_filename(request.blog_title)}{self.file_extension()}"
        filepath = output_dir / filename
        content_html = self._markdown_to_html(request.markdown_content or "")
        slug = request.slug or self.sanitize_filename(request.blog_title)
        canonical = f"{request.base_url.rstrip('/')}/{slug}"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self._escape(request.meta_title or request.blog_title)}</title>
<meta name="description" content="{self._escape(request.meta_description or '')}">
<meta name="author" content="{self._escape(request.author)}">
<meta name="keywords" content="{self._escape(', '.join(request.tags))}">
<link rel="canonical" href="{self._escape(canonical)}">

<!-- Open Graph -->
<meta property="og:title" content="{self._escape(request.meta_title or request.blog_title)}">
<meta property="og:description" content="{self._escape(request.meta_description or '')}">
<meta property="og:type" content="article">
<meta property="og:url" content="{self._escape(canonical)}">
<meta property="og:locale" content="en_US">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{self._escape(request.meta_title or request.blog_title)}">
<meta name="twitter:description" content="{self._escape(request.meta_description or '')}">

<!-- Article Schema -->
<script type="application/ld+json">
{json.dumps(self._article_schema(request, canonical), indent=2)}
</script>

<!-- Breadcrumb Schema -->
<script type="application/ld+json">
{json.dumps(self._breadcrumb_schema(request, canonical), indent=2)}
</script>
</head>
<body>
<article itemscope itemtype="https://schema.org/Article">
<header class="article-header">
<h1 itemprop="headline">{self._escape(request.blog_title)}</h1>
<div class="article-meta">
{self._meta_html(request)}
</div>
</header>

<div class="article-content" itemprop="articleBody">
{content_html}
</div>
</article>
</body>
</html>"""

        filepath.write_text(html, encoding="utf-8")
        size = filepath.stat().st_size
        return ExportFile(
            format=self.format_name(),
            filename=filename,
            size_bytes=size,
            size_display=self._size_display(size),
            download_url=f"/api/export/download/{filename}",
            mime_type=self.mime_type(),
        )

    def _markdown_to_html(self, md: str) -> str:
        """Convert Markdown to HTML."""
        import markdown as md_lib
        import bleach

        html = md_lib.markdown(
            md,
            extensions=['fenced_code', 'tables', 'codehilite', 'toc',
                       'sane_lists', 'attr_list', 'def_list'],
        )
        allowed_tags = list(bleach.ALLOWED_TAGS) + [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'code', 'span',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'img', 'figure', 'figcaption', 'hr', 'br',
            'blockquote', 'sup', 'sub', 'dl', 'dt', 'dd',
            'del', 'ins', 'kbd', 'samp', 'var', 'abbr',
        ]
        allowed_attrs = {
            'a': ['href', 'title', 'rel', 'target'],
            'img': ['src', 'alt', 'title', 'width', 'height', 'loading'],
            'code': ['class'],
            'pre': ['class'],
            'span': ['class'],
            'table': ['class'],
            'th': ['align', 'class'],
            'td': ['align', 'class'],
        }
        return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)

    def _meta_html(self, request: ExportRequest) -> str:
        parts = []
        if request.author:
            parts.append(f'<span class="meta-author">By {self._escape(request.author)}</span>')
        if request.publish_date:
            parts.append(f'<time datetime="{self._escape(request.publish_date)}">{self._escape(request.publish_date)}</time>')
        if request.reading_time:
            parts.append(f'<span class="meta-reading-time">{self._escape(request.reading_time)}</span>')
        if request.word_count:
            parts.append(f'<span class="meta-word-count">{request.word_count:,} words</span>')
        if request.category:
            parts.append(f'<span class="meta-category">{self._escape(request.category)}</span>')
        return ' · '.join(parts)

    def _article_schema(self, request: ExportRequest, canonical: str) -> dict:
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": request.meta_title or request.blog_title,
            "description": request.meta_description or "",
            "url": canonical,
        }
        if request.author:
            schema["author"] = {"@type": "Person", "name": request.author}
        if request.publish_date:
            schema["datePublished"] = request.publish_date
        schema["dateModified"] = datetime.now(timezone.utc).isoformat()
        if request.primary_keyword:
            schema["keywords"] = request.primary_keyword
        if request.tags:
            schema["keywords"] = ", ".join(request.tags)
        return schema

    def _breadcrumb_schema(self, request: ExportRequest, canonical: str) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": request.base_url.rstrip('/')},
                {"@type": "ListItem", "position": 2, "name": request.category or "Blog", "item": f"{request.base_url.rstrip('/')}/{request.category.lower() if request.category else 'blog'}"},
                {"@type": "ListItem", "position": 3, "name": request.blog_title, "item": canonical},
            ],
        }

    @staticmethod
    def _escape(text: str) -> str:
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#39;'))
