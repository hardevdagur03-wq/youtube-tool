"""Professional DOCX Exporter — generates enterprise Microsoft Word documents.

Features: Brand templates, professional heading styles, automatic TOC,
headers/footers, document properties, bookmarks.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from export_delivery.models import TemplateConfig

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.section import WD_ORIENT
    from docx.oxml.ns import qn
    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False

logger = logging.getLogger(__name__)


class ProfessionalDOCXExporter:
    """Generates professional Microsoft Word (.docx) documents.

    Usage::

        exporter = ProfessionalDOCXExporter()
        file_path = exporter.export(document, template_config)
    """

    def export(
        self,
        document: Any,
        output_dir: str = "",
        template_config: TemplateConfig | None = None,
    ) -> dict[str, Any]:
        """Export document as professional DOCX.

        Args:
            document: Document-like object.
            output_dir: Output directory.
            template_config: Template configuration.

        Returns:
            Dict with file info.
        """
        if not _HAS_DOCX:
            logger.warning("python-docx not installed, DOCX export unavailable")
            return {"format": "docx", "error": "python-docx not installed", "size_bytes": 0}

        template = template_config or TemplateConfig()
        doc = self._render(document, template)
        output_dir = output_dir or os.path.join(
            os.getcwd(), "exports_delivery", getattr(document, "project_id", "unknown")
        )
        os.makedirs(output_dir, exist_ok=True)

        slug = getattr(document, "slug", "") or self._slugify(getattr(document, "title", "export"))
        filename = f"{slug}.docx"
        filepath = os.path.join(output_dir, filename)

        doc.save(filepath)
        size = os.path.getsize(filepath)
        logger.info("DOCX exported: %s (%d bytes)", filename, size)

        return {
            "format": "docx",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }

    def _render(self, document: Any, template: TemplateConfig) -> Any:
        """Render the DOCX document."""
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor, Cm

        doc = Document()
        self._setup_styles(doc, template)

        title = getattr(document, "title", "")
        author = getattr(document, "author", "")
        meta_desc = getattr(document, "meta_description", "")
        reading_time = getattr(document, "reading_time", 0)
        word_count = getattr(document, "word_count", 0)
        publish_date = getattr(document, "publish_date", "") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Document properties
        doc.core_properties.title = title
        doc.core_properties.author = author or "AI Blog Generator"
        doc.core_properties.subject = meta_desc

        # Cover page
        if template.cover_page:
            self._add_cover_page(doc, title, author, publish_date, reading_time, template)

        # Metadata table
        self._add_metadata_table(doc, author, publish_date, reading_time, word_count)

        if meta_desc:
            p = doc.add_paragraph(meta_desc)
            p.italic = True

        # Table of Contents
        if template.toc_enabled:
            self._add_toc(doc, document)

        # Introduction
        intro = getattr(document, "introduction", "")
        if intro:
            doc.add_heading("Introduction", level=1)
            doc.add_paragraph(intro)

        # Sections
        sections = getattr(document, "sections", []) or []
        for section in sections:
            self._add_section(doc, section)

        # FAQ
        faq = getattr(document, "faq", []) or []
        if faq:
            doc.add_heading("Frequently Asked Questions", level=1)
            for item in faq:
                q = item.get("question", "") if isinstance(item, dict) else getattr(item, "question", "")
                a = item.get("answer", "") if isinstance(item, dict) else getattr(item, "answer", "")
                if q:
                    p = doc.add_paragraph(q)
                    p.runs[0].bold = True if p.runs else False
                    p.style = doc.styles["Heading 3"] if hasattr(doc.styles, "Heading 3") else p
                if a:
                    doc.add_paragraph(a)

        # Conclusion
        conclusion = getattr(document, "conclusion", "")
        if conclusion:
            doc.add_heading("Conclusion", level=1)
            doc.add_paragraph(conclusion)

        # CTA
        cta = getattr(document, "call_to_action", "")
        if cta:
            p = doc.add_paragraph(cta)
            for run in p.runs:
                run.font.color.rgb = RGBColor(
                    *self._hex_to_rgb(template.brand_color)
                )

        # References
        refs = getattr(document, "references", []) or []
        if refs:
            doc.add_heading("References", level=1)
            for i, ref in enumerate(refs, 1):
                url = ref.get("url", "") if isinstance(ref, dict) else getattr(ref, "url", "")
                title_ref = ref.get("title", "") if isinstance(ref, dict) else getattr(ref, "title", "")
                text = f"{i}. {title_ref or url}" if url else f"{i}. {ref}"
                doc.add_paragraph(text, style="List Number")

        # Footer with page numbers
        for section in doc.sections:
            footer = section.footer
            footer.is_linked_to_previous = False
            p = footer.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            fld_char_begin = run._element.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "begin"})
            run._element.addnext(fld_char_begin)
            instr = run._element.makeelement(qn("w:instrText"), {})
            instr.text = " PAGE "
            fld_char_begin.addnext(instr)

        return doc

    def _setup_styles(self, doc: Any, template: TemplateConfig) -> None:
        from docx.shared import Pt, RGBColor
        style = doc.styles["Normal"]
        style.font.size = Pt(template.font_size_base)
        style.paragraph_format.line_spacing = template.line_height

    def _add_cover_page(self, doc: Any, title: str, author: str, date: str, reading_time: int, template: TemplateConfig) -> None:
        from docx.shared import Pt, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        for _ in range(6):
            doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(title or "")
        run.font.size = Pt(28)
        run.bold = True
        if author:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(f"By {author}")
            run.font.size = Pt(14)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{date}  •  {reading_time} min read" if reading_time else date)
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(128, 128, 128)
        doc.add_page_break()

    def _add_metadata_table(self, doc: Any, author: str, date: str, reading_time: int, word_count: int) -> None:
        rows = []
        if author:
            rows.append(("Author", author))
        if date:
            rows.append(("Date", date))
        if reading_time:
            rows.append(("Reading Time", f"{reading_time} min"))
        if word_count:
            rows.append(("Word Count", str(word_count)))
        if rows:
            table = doc.add_table(rows=len(rows), cols=2)
            table.style = "Light Grid Accent 1"
            for i, (k, v) in enumerate(rows):
                table.rows[i].cells[0].text = k
                table.rows[i].cells[1].text = v
                table.rows[i].cells[0].paragraphs[0].runs[0].bold = True

    def _add_toc(self, doc: Any, document: Any) -> None:
        sections = getattr(document, "sections", []) or []
        if sections:
            doc.add_heading("Table of Contents", level=1)
            for section in sections:
                heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
                if heading:
                    doc.add_paragraph(heading, style="List Bullet")
            doc.add_page_break()

    def _add_section(self, doc: Any, section: Any) -> None:
        heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
        content = section.get("content", "") if isinstance(section, dict) else getattr(section, "content", "")
        level = section.get("level", 2) if isinstance(section, dict) else 2
        subsections = section.get("subsections", []) if isinstance(section, dict) else getattr(section, "subsections", [])
        callouts = section.get("callout_boxes", []) if isinstance(section, dict) else getattr(section, "callout_boxes", [])

        if heading:
            doc.add_heading(heading, level=min(level, 6))
        if content:
            doc.add_paragraph(content)
        for sub in subsections or []:
            sub_h = sub.get("heading", "") if isinstance(sub, dict) else getattr(sub, "heading", "")
            sub_c = sub.get("content", "") if isinstance(sub, dict) else getattr(sub, "content", "")
            if sub_h:
                doc.add_heading(sub_h, level=min(level + 1, 6))
            if sub_c:
                doc.add_paragraph(sub_c)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _slugify(text: str) -> str:
        if not text:
            return "untitled"
        slug = text.lower().strip().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug.strip("-") or "untitled"
