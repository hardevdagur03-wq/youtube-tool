"""Professional PDF Exporter — generates publication-quality PDFs.

Features: Professional typography, A4/Letter/Custom, TOC with bookmarks,
clickable links, headers/footers, page numbers, document metadata.
Uses weasyprint for CSS-based rendering when available, fpdf2 fallback.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from export_delivery.models import TemplateConfig

logger = logging.getLogger(__name__)


class ProfessionalPDFExporter:
    """Generates publication-quality PDF documents.

    Uses weasyprint for professional CSS-based rendering (with headers,
    footers, bookmarks) with fpdf2 as fallback.

    Usage::

        exporter = ProfessionalPDFExporter()
        file_path = exporter.export(document, template_config)
    """

    def __init__(self) -> None:
        self._has_weasyprint = False
        self._has_fpdf = False
        try:
            import weasyprint
            self._has_weasyprint = True
        except ImportError:
            pass
        try:
            from fpdf import FPDF
            self._has_fpdf = True
        except ImportError:
            pass

    def export(
        self,
        document: Any,
        output_dir: str = "",
        template_config: TemplateConfig | None = None,
    ) -> dict[str, Any]:
        """Export document as professional PDF.

        Args:
            document: Document-like object.
            output_dir: Output directory.
            template_config: Template configuration.

        Returns:
            Dict with file info.
        """
        if not self._has_weasyprint and not self._has_fpdf:
            logger.warning("No PDF library available (weasyprint or fpdf)")
            return {"format": "pdf", "error": "No PDF library available", "size_bytes": 0}

        template = template_config or TemplateConfig()

        if self._has_weasyprint:
            return self._export_weasyprint(document, output_dir, template)
        return self._export_fpdf(document, output_dir, template)

    def _export_weasyprint(
        self, document: Any, output_dir: str, template: TemplateConfig
    ) -> dict[str, Any]:
        """Export PDF using weasyprint for professional CSS rendering."""
        from weasyprint import HTML

        output_dir = output_dir or os.path.join(
            os.getcwd(), "exports_delivery", getattr(document, "project_id", "unknown")
        )
        os.makedirs(output_dir, exist_ok=True)

        slug = getattr(document, "slug", "") or self._slugify(getattr(document, "title", "export"))
        filename = f"{slug}.pdf"
        filepath = os.path.join(output_dir, filename)

        # Build HTML with print CSS for PDF rendering
        html_content = self._build_html_for_pdf(document, template)
        HTML(string=html_content).write_pdf(filepath)

        size = os.path.getsize(filepath)
        logger.info("PDF exported (weasyprint): %s (%d bytes)", filename, size)

        return {
            "format": "pdf",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "mime_type": "application/pdf",
        }

    def _build_html_for_pdf(self, document: Any, template: TemplateConfig) -> str:
        """Build HTML optimized for PDF rendering with weasyprint."""
        from html import escape as html_escape
        title = getattr(document, "title", "")
        author = getattr(document, "author", "")
        meta_desc = getattr(document, "meta_description", "")
        reading_time = getattr(document, "reading_time", 0)
        word_count = getattr(document, "word_count", 0)
        publish_date = getattr(document, "publish_date", "") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        sections_html = ""
        for section in getattr(document, "sections", []) or []:
            heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
            content = section.get("content", "") if isinstance(section, dict) else getattr(section, "content", "")
            if heading:
                sections_html += f"<h2>{html_escape(heading)}</h2>"
            if content:
                sections_html += f"<p>{html_escape(content)}</p>"
            for sub in (section.get("subsections", []) if isinstance(section, dict) else getattr(section, "subsections", [])):
                sub_h = sub.get("heading", "") if isinstance(sub, dict) else getattr(sub, "heading", "")
                sub_c = sub.get("content", "") if isinstance(sub, dict) else getattr(sub, "content", "")
                if sub_h:
                    sections_html += f"<h3>{html_escape(sub_h)}</h3>"
                if sub_c:
                    sections_html += f"<p>{html_escape(sub_c)}</p>"

        faq_html = ""
        for item in getattr(document, "faq", []) or []:
            q = item.get("question", "") if isinstance(item, dict) else getattr(item, "question", "")
            a = item.get("answer", "") if isinstance(item, dict) else getattr(item, "answer", "")
            if q:
                faq_html += f"<h3>{html_escape(q)}</h3>"
            if a:
                faq_html += f"<p>{html_escape(a)}</p>"

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
@page {{ size: {template.page_size}; margin: {template.page_margin_mm}mm;
  @top-center {{ content: element(header); font-size: 9pt; color: #666; }}
  @bottom-center {{ content: counter(page); font-size: 9pt; color: #666; }}
}}
body {{ font-family: {template.font_family}; font-size: {template.font_size_base}pt; line-height: {template.line_height}; color: #1a1a1a; }}
h1, h2, h3 {{ font-family: {template.font_family_heading}; color: {template.secondary_color}; }}
h1 {{ font-size: {template.font_size_base * template.font_size_heading_scale * template.font_size_heading_scale}pt; page-break-before: always; }}
h1:first-of-type {{ page-break-before: avoid; }}
h2 {{ font-size: {template.font_size_base * template.font_size_heading_scale}pt; }}
code {{ font-family: {template.font_family_mono}; font-size: 90%; }}
pre {{ background: #f5f5f5; padding: 1em; border-radius: 4px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px; }}
.cover {{ text-align: center; padding-top: 40%; }}
.cover h1 {{ font-size: 28pt; margin-bottom: 0.5em; }}
.cover p {{ font-size: 12pt; color: #666; }}
.toc {{ page-break-after: always; }}
.toc a {{ color: inherit; text-decoration: none; }}
.meta {{ font-size: 10pt; color: #666; margin-bottom: 2em; }}
</style>
</head><body>
<div class="cover">
  <h1>{html_escape(title)}</h1>
  <p>{'By ' + html_escape(author) if author else ''}</p>
  <p>{publish_date}{f'  •  {reading_time} min read' if reading_time else ''}</p>
</div>
<div class="meta"><p>{f'Word Count: {word_count}' if word_count else ''}</p></div>
<blockquote>{html_escape(meta_desc)}</blockquote>
<div class="toc"><h2>Table of Contents</h2>
{''.join(f'<p><a href="#{html_escape(s.get("heading", "")).lower().replace(" ", "-")}"></a>{html_escape(s.get("heading", ""))}</p>' for s in (getattr(document, "sections", []) or []) if s.get("heading", ""))}
</div>
<h2>Introduction</h2><p>{html_escape(getattr(document, "introduction", ""))}</p>
{sections_html}
{f'<h2>Frequently Asked Questions</h2>{faq_html}' if faq_html else ''}
<h2>Conclusion</h2><p>{html_escape(getattr(document, "conclusion", ""))}</p>
</body></html>"""

    def _export_fpdf(
        self, document: Any, output_dir: str, template: TemplateConfig
    ) -> dict[str, Any]:
        """Fallback PDF export using fpdf2."""
        from fpdf import FPDF

        output_dir = output_dir or os.path.join(
            os.getcwd(), "exports_delivery", getattr(document, "project_id", "unknown")
        )
        os.makedirs(output_dir, exist_ok=True)

        slug = getattr(document, "slug", "") or self._slugify(getattr(document, "title", "export"))
        filename = f"{slug}.pdf"
        filepath = os.path.join(output_dir, filename)

        pdf = FPDF()
        page_w = 210 if template.page_size == "A4" else 216
        pdf.set_auto_page_break(auto=True, margin=template.page_margin_mm)

        # Cover
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 28)
        pdf.ln(60)
        pdf.cell(page_w - 20, 15, getattr(document, "title", ""), align="C")
        pdf.ln(20)
        pdf.set_font("Helvetica", "", 14)
        pdf.cell(page_w - 20, 10, f"By {getattr(document, 'author', '')}", align="C")
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(page_w - 20, 10, getattr(document, "publish_date", ""), align="C")

        # Sections
        for section in getattr(document, "sections", []) or []:
            pdf.add_page()
            heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
            content = section.get("content", "") if isinstance(section, dict) else getattr(section, "content", "")
            if heading:
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, heading)
                pdf.ln(15)
            if content:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, content)

        pdf.output(filepath)
        size = os.path.getsize(filepath)
        logger.info("PDF exported (fpdf2): %s (%d bytes)", filename, size)

        return {
            "format": "pdf",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "mime_type": "application/pdf",
        }

    @staticmethod
    def _slugify(text: str) -> str:
        if not text:
            return "untitled"
        slug = text.lower().strip().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug.strip("-") or "untitled"
