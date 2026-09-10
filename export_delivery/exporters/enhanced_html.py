"""Enhanced HTML Exporter — generates semantic HTML5 with SEO and accessibility.

Features: OpenGraph, Twitter Cards, JSON-LD Schema.org, responsive images,
syntax highlighting, dark mode, print styles, ARIA labels.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from export_delivery.models import TemplateConfig

logger = logging.getLogger(__name__)


class EnhancedHTMLExporter:
    """Generates semantic HTML5 with full SEO and accessibility support.

    Usage::

        exporter = EnhancedHTMLExporter()
        file_path = exporter.export(document, template_config)
    """

    def export(
        self,
        document: Any,
        output_dir: str = "",
        template_config: TemplateConfig | None = None,
    ) -> dict[str, Any]:
        """Export document as enhanced HTML5.

        Args:
            document: Document-like object.
            output_dir: Output directory.
            template_config: Template configuration.

        Returns:
            Dict with file info.
        """
        template = template_config or TemplateConfig()
        html = self._render(document, template)
        output_dir = output_dir or os.path.join(
            os.getcwd(), "exports_delivery", getattr(document, "project_id", "unknown")
        )
        os.makedirs(output_dir, exist_ok=True)

        slug = getattr(document, "slug", "") or self._slugify(getattr(document, "title", "export"))
        filename = f"{slug}.html"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        size = os.path.getsize(filepath)
        logger.info("HTML exported: %s (%d bytes)", filename, size)

        return {
            "format": "html",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "mime_type": "text/html",
        }

    def _render(self, document: Any, template: TemplateConfig) -> str:
        """Render the full HTML document."""
        title = getattr(document, "title", "")
        meta_desc = getattr(document, "meta_description", "") or ""
        author = getattr(document, "author", "") or ""
        base_url = getattr(document, "base_url", "") or ""
        canonical = f"{base_url}/{self._slugify(title)}" if base_url and title else ""
        tags = getattr(document, "tags", []) or []
        category = getattr(document, "category", "") or ""
        word_count = getattr(document, "word_count", 0) or 0
        reading_time = getattr(document, "reading_time", 0) or 0
        publish_date = getattr(document, "publish_date", "") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Build body content
        body_parts = []

        # Title
        if title:
            body_parts.append(f'<h1 id="title">{self._escape(title)}</h1>')

        # Meta block
        meta_block = "<dl class='meta'>"
        if author:
            meta_block += f"<dt>Author</dt><dd>{self._escape(author)}</dd>"
        meta_block += f"<dt>Date</dt><dd>{publish_date}</dd>"
        if reading_time:
            meta_block += f"<dt>Reading Time</dt><dd>{reading_time} min</dd>"
        if word_count:
            meta_block += f"<dt>Word Count</dt><dd>{word_count}</dd>"
        if category:
            meta_block += f"<dt>Category</dt><dd>{self._escape(category)}</dd>"
        if tags:
            meta_block += f"<dt>Tags</dt><dd>{', '.join(self._escape(t) for t in tags)}</dd>"
        meta_block += "</dl>"
        body_parts.append(meta_block)

        if meta_desc:
            body_parts.append(f"<blockquote>{self._escape(meta_desc)}</blockquote>")

        # TOC
        if template.toc_enabled:
            toc = self._render_toc(document)
            if toc:
                body_parts.append('<nav aria-label="Table of Contents" role="navigation">')
                body_parts.append("<h2>Table of Contents</h2>")
                body_parts.append(toc)
                body_parts.append("</nav>")
                body_parts.append("<hr>")

        # Introduction
        intro = getattr(document, "introduction", "")
        if intro:
            body_parts.append("<section id='introduction' aria-label='Introduction'>")
            body_parts.append("<h2>Introduction</h2>")
            body_parts.append(f"<p>{self._markdown_to_html(intro)}</p>")
            body_parts.append("</section>")

        # Sections
        sections = getattr(document, "sections", []) or []
        for section in sections:
            body_parts.append(self._render_section_html(section))

        # FAQ
        faq = getattr(document, "faq", []) or []
        if faq:
            body_parts.append("<section id='faq' aria-label='Frequently Asked Questions'>")
            body_parts.append("<h2>Frequently Asked Questions</h2>")
            body_parts.append('<div itemscope itemtype="https://schema.org/FAQPage">')
            for item in faq:
                q = item.get("question", "") if isinstance(item, dict) else getattr(item, "question", "")
                a = item.get("answer", "") if isinstance(item, dict) else getattr(item, "answer", "")
                if q and a:
                    body_parts.append(f'<h3 itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">')
                    body_parts.append(f'<span itemprop="name">{self._escape(q)}</span></h3>')
                    body_parts.append(f'<div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">')
                    body_parts.append(f'<p itemprop="text">{self._markdown_to_html(a)}</p></div>')
            body_parts.append("</div></section>")

        # Conclusion
        conclusion = getattr(document, "conclusion", "")
        if conclusion:
            body_parts.append("<section id='conclusion' aria-label='Conclusion'>")
            body_parts.append("<h2>Conclusion</h2>")
            body_parts.append(f"<p>{self._markdown_to_html(conclusion)}</p>")
            body_parts.append("</section>")

        # CTA
        cta = getattr(document, "call_to_action", "")
        if cta:
            body_parts.append(f"<div class='cta'>{self._markdown_to_html(cta)}</div>")

        # References
        refs = getattr(document, "references", []) or []
        if refs:
            body_parts.append("<section id='references'>")
            body_parts.append("<h2>References</h2>")
            body_parts.append("<ol>")
            for ref in refs:
                url = ref.get("url", "") if isinstance(ref, dict) else getattr(ref, "url", "")
                title_ref = ref.get("title", "") if isinstance(ref, dict) else getattr(ref, "title", "")
                if url:
                    body_parts.append(f'<li><a href="{self._escape(url)}" rel="noopener noreferrer">{self._escape(title_ref or url)}</a></li>')
                elif isinstance(ref, str):
                    body_parts.append(f"<li>{self._escape(ref)}</li>")
            body_parts.append("</ol></section>")

        body_content = "\n".join(body_parts)

        # Build full HTML
        css_vars = "; ".join(f"{k}: {v}" for k, v in template.css_variables.items()) if hasattr(template, 'css_variables') else ""
        html = f"""<!DOCTYPE html>
<html lang="en" itemscope itemtype="https://schema.org/Article">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self._escape(title)}</title>
<meta name="description" content="{self._escape(meta_desc)}">
<meta name="author" content="{self._escape(author)}">
{self._render_opengraph(title, meta_desc, canonical, author, publish_date)}
{self._render_twitter_card(title, meta_desc, canonical)}
{self._render_json_ld(document, title, meta_desc, author, publish_date, canonical)}
<link rel="canonical" href="{canonical}">
<style>
:root {{ {css_vars} font-family: {template.font_family}; font-size: {template.font_size_base}px; line-height: {template.line_height}; }}
body {{ max-width: 800px; margin: 0 auto; padding: 2em; color: #1a1a1a; background: #fff; }}
h1, h2, h3, h4 {{ font-family: {template.font_family_heading}; color: {template.secondary_color}; margin-top: 1.5em; }}
code, pre {{ font-family: {template.font_family_mono}; }}
pre {{ background: #f5f5f5; padding: 1em; border-radius: 4px; overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f5f5f5; }}
blockquote {{ border-left: 4px solid {template.brand_color}; margin: 1em 0; padding: 0.5em 1em; background: #f9fafb; }}
@media (prefers-color-scheme: dark) {{
body {{ color: #e5e7eb; background: #111827; }}
pre {{ background: #1f2937; }}
th {{ background: #1f2937; }}
td {{ border-color: #374151; }}
blockquote {{ background: #1f2937; }}
a {{ color: #60a5fa; }}
}}
@media print {{
body {{ max-width: none; padding: 0; }}
nav, .cta {{ display: none; }}
}}
.cta {{ background: {template.brand_color}; color: #fff; padding: 1em; border-radius: 8px; text-align: center; margin: 2em 0; }}
.cta a {{ color: #fff; text-decoration: underline; }}
meta dd {{ margin: 0; }}
meta dt {{ font-weight: bold; }}
</style>
</head>
<body>
<article>
{body_content}
</article>
</body>
</html>"""
        return html

    def _render_opengraph(self, title: str, desc: str, url: str, author: str, date: str) -> str:
        if not title:
            return ""
        lines = [
            f'<meta property="og:title" content="{self._escape(title)}">',
            f'<meta property="og:description" content="{self._escape(desc)}">',
            f'<meta property="og:type" content="article">',
        ]
        if url:
            lines.append(f'<meta property="og:url" content="{url}">')
        if author:
            lines.append(f'<meta property="og:locale" content="en_US">')
        lines.append(f'<meta property="article:published_time" content="{date}">')
        return "\n".join(lines)

    def _render_twitter_card(self, title: str, desc: str, url: str) -> str:
        if not title:
            return ""
        lines = [
            f'<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{self._escape(title)}">',
            f'<meta name="twitter:description" content="{self._escape(desc)}">',
        ]
        if url:
            lines.append(f'<meta name="twitter:url" content="{url}">')
        return "\n".join(lines)

    def _render_json_ld(self, document: Any, title: str, desc: str, author: str, date: str, url: str) -> str:
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": desc,
            "author": {"@type": "Person", "name": author} if author else None,
            "datePublished": date,
            "wordCount": getattr(document, "word_count", 0),
        }
        if url:
            schema["url"] = url
        schema = {k: v for k, v in schema.items() if v is not None}
        import json
        return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'

    def _render_toc(self, document: Any) -> str:
        sections = getattr(document, "sections", []) or []
        items = []
        for section in sections:
            heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
            if heading:
                anchor = heading.lower().replace(" ", "-").replace("?", "").replace("!", "")
                items.append(f'<li><a href="#{anchor}">{self._escape(heading)}</a></li>')
        return f"<ul>\n" + "\n".join(items) + "\n</ul>" if items else ""

    def _render_section_html(self, section: Any) -> str:
        parts = []
        heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
        content = section.get("content", "") if isinstance(section, dict) else getattr(section, "content", "")
        level = section.get("level", 2) if isinstance(section, dict) else 2
        subsections = section.get("subsections", []) if isinstance(section, dict) else getattr(section, "subsections", [])
        callouts = section.get("callout_boxes", []) if isinstance(section, dict) else getattr(section, "callout_boxes", [])

        tag = f"h{min(level, 6)}"
        if heading:
            anchor = heading.lower().replace(" ", "-").replace("?", "").replace("!", "")
            parts.append(f'<section aria-label="{self._escape(heading)}">')
            parts.append(f'<{tag} id="{anchor}">{self._escape(heading)}</{tag}>')
        if content:
            parts.append(f"<p>{self._markdown_to_html(content)}</p>")
        for callout in callouts or []:
            ct_text = callout.get("text", "") if isinstance(callout, dict) else getattr(callout, "text", "")
            if ct_text:
                parts.append(f"<div class='callout'>{self._markdown_to_html(ct_text)}</div>")
        for sub in subsections or []:
            sub_h = sub.get("heading", "") if isinstance(sub, dict) else getattr(sub, "heading", "")
            sub_c = sub.get("content", "") if isinstance(sub, dict) else getattr(sub, "content", "")
            if sub_h:
                parts.append(f"<h{min(level+1, 6)}>{self._escape(sub_h)}</h{min(level+1, 6)}>")
            if sub_c:
                parts.append(f"<p>{self._markdown_to_html(sub_c)}</p>")
        if heading:
            parts.append("</section>")
        return "\n".join(parts)

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """Simple Markdown to HTML conversion (no external deps)."""
        from html import escape
        text = escape(text)
        text = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        text = re.sub(r'\n\n', r'</p><p>', text)
        return f"<p>{text}</p>"

    @staticmethod
    def _escape(text: str) -> str:
        """Escape HTML entities."""
        from html import escape
        return escape(text)

    @staticmethod
    def _slugify(text: str) -> str:
        if not text:
            return "untitled"
        slug = text.lower().strip().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug.strip("-") or "untitled"
