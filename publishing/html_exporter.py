from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from publishing.models import (
    DocumentModel, ExportFileInfo, ExportFormat, FORMAT_EXTENSIONS, FORMAT_MIME_TYPES,
    OpenGraphData, TwitterCardData, SchemaMarkup,
)

logger = logging.getLogger(__name__)


def _md_to_html(md: str) -> str:
    html = md
    html = html.replace("&", "&amp;")
    html = html.replace("<", "&lt;")
    html = html.replace(">", "&gt;")

    html = re.sub(r"```(\w*)\n([\s\S]*?)```", lambda m:
        f'<pre class="code-block language-{m.group(1) or "text"}"><code>{m.group(2).strip()}</code></pre>', html)

    html = re.sub(r"`([^`]+)`", r'<code class="inline-code">\1</code>', html)

    html = re.sub(r"^######\s+(.+)$", r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r"^#####\s+(.+)$", r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r"^####\s+(.+)$", r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r"^###\s+(.+)$", r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r"^##\s+(.+)$", r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r"^#\s+(.+)$", r'<h1>\1</h1>', html, flags=re.MULTILINE)

    html = re.sub(r"^>\s+(.*)$", r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    html = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<figure><img src="\2" alt="\1" loading="lazy" /><figcaption>\1</figcaption></figure>', html)

    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', html)

    html = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', html)
    html = re.sub(r"\*(.+?)\*", r'<em>\1</em>', html)
    html = re.sub(r"~~(.+?)~~", r'<del>\1</del>', html)

    html = re.sub(r"^---\s*$", r'<hr />', html, flags=re.MULTILINE)

    html = re.sub(r"^\|(.+)\|$", lambda m: _process_table_row(m.group(1)), html, flags=re.MULTILINE)

    return html


def _process_table_row(row_content: str) -> str:
    cells = [c.strip() for c in row_content.split("|")]
    if all(re.match(r"^:?-+:?$", c) for c in cells if c.strip()):
        return ""
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


class HTMLExporter:
    def render(self, document: DocumentModel, base_url: str = "",
               og: OpenGraphData | None = None, twitter: TwitterCardData | None = None,
               schema: list[SchemaMarkup] | None = None) -> str:
        content_html = _md_to_html(document.content)
        og = og or OpenGraphData()
        twitter = twitter or TwitterCardData()

        title_escaped = self._escape(document.seo_title or document.title)
        desc_escaped = self._escape(document.meta_description or "")
        author_escaped = self._escape(document.author)

        og_tags = ""
        if og.title:
            og_tags += f'\n    <meta property="og:title" content="{self._escape(og.title)}" />'
            og_tags += f'\n    <meta name="twitter:title" content="{self._escape(og.title)}" />'
        if og.description:
            og_tags += f'\n    <meta property="og:description" content="{self._escape(og.description)}" />'
            og_tags += f'\n    <meta name="twitter:description" content="{self._escape(og.description)}" />'
        if og.url or base_url:
            url = og.url or base_url
            og_tags += f'\n    <meta property="og:url" content="{self._escape(url)}" />'
            og_tags += f'\n    <link rel="canonical" href="{self._escape(url)}" />'
        if og.image:
            og_tags += f'\n    <meta property="og:image" content="{self._escape(og.image)}" />'
            og_tags += f'\n    <meta name="twitter:image" content="{self._escape(og.image)}" />'
        if og.type:
            og_tags += f'\n    <meta property="og:type" content="{self._escape(og.type)}" />'
        if og.locale:
            og_tags += f'\n    <meta property="og:locale" content="{self._escape(og.locale)}" />'
        if og.published_time:
            og_tags += f'\n    <meta property="article:published_time" content="{self._escape(og.published_time)}" />'
        if og.author:
            og_tags += f'\n    <meta name="author" content="{self._escape(og.author)}" />'
        og_tags += f'\n    <meta name="twitter:card" content="{self._escape(twitter.card or "summary_large_image")}" />'
        if twitter.site:
            og_tags += f'\n    <meta name="twitter:site" content="{self._escape(twitter.site)}" />'

        schema_html = ""
        if schema:
            for s in schema:
                schema_html += f'\n    <script type="application/ld+json">\n{json.dumps(s.data, indent=2)}\n    </script>'

        tags_html = ""
        if document.tags:
            tags_html = '\n    <meta name="keywords" content="' + self._escape(", ".join(document.tags)) + '" />'

        html = f"""<!DOCTYPE html>
<html lang="{document.language or 'en'}">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title_escaped}</title>
    <meta name="description" content="{desc_escaped}" />
    <meta name="author" content="{author_escaped}" />{tags_html}{og_tags}{schema_html}
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1a1a2e; background: #ffffff; max-width: 800px; margin: 0 auto; padding: 2rem; }}
        h1 {{ font-size: 2rem; margin: 1.5rem 0 0.5rem; color: #111827; line-height: 1.3; }}
        h2 {{ font-size: 1.5rem; margin: 1.5rem 0 0.5rem; color: #1f2937; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.25rem; }}
        h3 {{ font-size: 1.25rem; margin: 1.25rem 0 0.5rem; color: #374151; }}
        h4 {{ font-size: 1.1rem; margin: 1rem 0 0.5rem; color: #4b5563; }}
        h5, h6 {{ font-size: 1rem; margin: 1rem 0 0.5rem; color: #6b7280; }}
        p {{ margin: 0.75rem 0; color: #374151; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        strong {{ font-weight: 600; color: #111827; }}
        blockquote {{ border-left: 4px solid #d1d5db; margin: 1rem 0; padding: 0.5rem 1rem; color: #6b7280; background: #f9fafb; }}
        code {{ font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 0.875em; }}
        .inline-code {{ background: #f3f4f6; padding: 0.15rem 0.3rem; border-radius: 4px; color: #dc2626; }}
        .code-block {{ background: #1f2937; color: #f3f4f6; padding: 1rem; border-radius: 8px; overflow-x: auto; margin: 1rem 0; }}
        .code-block code {{ color: #e5e7eb; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 1rem 0; }}
        figure {{ margin: 1rem 0; text-align: center; }}
        figcaption {{ font-size: 0.875rem; color: #9ca3af; margin-top: 0.25rem; }}
        hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 2rem 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }}
        th {{ background: #f9fafb; font-weight: 600; color: #374151; }}
        ul, ol {{ margin: 0.75rem 0; padding-left: 1.5rem; color: #374151; }}
        li {{ margin: 0.25rem 0; }}
        .meta-header {{ background: #f9fafb; border-radius: 8px; padding: 1rem; margin: 1rem 0; font-size: 0.875rem; color: #6b7280; }}
        .meta-header strong {{ color: #374151; }}
        @media (prefers-color-scheme: dark) {{
            body {{ background: #0f172a; color: #e2e8f0; }}
            h1, h2, h3, h4, h5, h6, strong {{ color: #f1f5f9; }}
            p, li {{ color: #cbd5e1; }}
            blockquote {{ background: #1e293b; border-color: #334155; color: #94a3b8; }}
            .inline-code {{ background: #1e293b; color: #f87171; }}
            .code-block {{ background: #000000; }}
            th, td {{ border-color: #334155; }}
            th {{ background: #1e293b; color: #e2e8f0; }}
            .meta-header {{ background: #1e293b; color: #94a3b8; }}
            .meta-header strong {{ color: #e2e8f0; }}
            a {{ color: #60a5fa; }}
        }}
        @media print {{
            body {{ padding: 0; max-width: none; }}
            .code-block {{ break-inside: avoid; }}
            img {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <article>
        <header>
            <h1>{title_escaped}</h1>
            <div class="meta-header">
                <strong>Author:</strong> {author_escaped}"""
        if document.publish_date:
            html += f'\n                <br /><strong>Published:</strong> {self._escape(document.publish_date)}'
        if document.reading_time_minutes:
            html += f'\n                <br /><strong>Reading time:</strong> {document.reading_time_minutes} min'
        if document.word_count:
            html += f'\n                <br /><strong>Word count:</strong> {document.word_count}'
        if document.category:
            html += f'\n                <br /><strong>Category:</strong> {self._escape(document.category)}'

        html += """
            </div>
        </header>
        <div class="content">
"""
        html += content_html

        html += """
        </div>
    </article>
</body>
</html>"""

        return html

    def export(self, document: DocumentModel, output_dir: Path, base_url: str = "",
               og: OpenGraphData | None = None, twitter: TwitterCardData | None = None,
               schema: list[SchemaMarkup] | None = None) -> ExportFileInfo:
        content = self.render(document, base_url, og, twitter, schema)
        filename = f"blog{FORMAT_EXTENSIONS[ExportFormat.HTML]}"
        filepath = output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        size = filepath.stat().st_size
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
        return ExportFileInfo(
            format=ExportFormat.HTML,
            filename=filename,
            size_bytes=size,
            size_display=self._size_display(size),
            mime_type=FORMAT_MIME_TYPES[ExportFormat.HTML],
            checksum=checksum,
        )

    @staticmethod
    def _escape(text: str) -> str:
        return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;").replace("'", "&#39;"))

    @staticmethod
    def _size_display(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"


import json
