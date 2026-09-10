from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from fpdf import FPDF

from publishing.models import (
    DocumentModel, ExportFileInfo, ExportFormat, FORMAT_EXTENSIONS, FORMAT_MIME_TYPES,
)

logger = logging.getLogger(__name__)

BRAND_GREEN = (5, 150, 105)
BRAND_DARK = (31, 41, 55)
BRAND_ACCENT = (124, 58, 237)
TEXT_COLOR = (26, 26, 46)
MUTED_COLOR = (107, 114, 128)
BG_LIGHT = (249, 250, 251)
BORDER_COLOR = (229, 231, 235)


class ExportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self._in_code_block = False

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*MUTED_COLOR)
            self.cell(0, 8, "AI-Generated Blog", align="L")
            self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="R", new_x="LMARGIN", new_y="NEXT")

    def footer(self):
        pass


class PDFExporter:
    def export(self, document: DocumentModel, output_dir: Path, base_url: str = "") -> ExportFileInfo:
        pdf = ExportPDF()
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)

        self._add_cover_page(pdf, document)
        pdf.add_page()

        self._add_toc(pdf, document)
        pdf.add_page()

        if document.introduction:
            self._add_introduction(pdf, document)

        for section in document.sections:
            self._add_section(pdf, section)

        if document.faq:
            self._add_faq(pdf, document)

        if document.conclusion:
            self._add_conclusion(pdf, document)

        if document.call_to_action:
            self._add_cta(pdf, document)

        if document.references:
            self._add_references(pdf, document)

        filename = f"blog{FORMAT_EXTENSIONS[ExportFormat.PDF]}"
        filepath = output_dir / filename
        pdf.output(str(filepath))
        size = filepath.stat().st_size
        checksum = hashlib.sha256(filepath.read_bytes()).hexdigest()[:32]
        return ExportFileInfo(
            format=ExportFormat.PDF,
            filename=filename,
            size_bytes=size,
            size_display=self._size_display(size),
            mime_type=FORMAT_MIME_TYPES[ExportFormat.PDF],
            checksum=checksum,
        )

    def _add_cover_page(self, pdf: ExportPDF, document: DocumentModel) -> None:
        pdf.add_page()
        pdf.ln(50)
        pdf.set_font("Helvetica", "B", 28)
        pdf.set_text_color(*BRAND_GREEN)
        pdf.multi_cell(0, 14, document.seo_title or document.title, align="C")
        pdf.ln(10)
        if document.meta_description:
            pdf.set_font("Helvetica", "I", 12)
            pdf.set_text_color(*MUTED_COLOR)
            pdf.multi_cell(0, 7, document.meta_description, align="C")
        pdf.ln(15)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*MUTED_COLOR)
        meta_parts = []
        if document.author:
            meta_parts.append(f"By {document.author}")
        if document.publish_date:
            meta_parts.append(document.publish_date)
        if document.reading_time_minutes:
            meta_parts.append(f"{document.reading_time_minutes} min read")
        if meta_parts:
            pdf.cell(0, 6, "  |  ".join(meta_parts), align="C", new_x="LMARGIN", new_y="NEXT")

    def _add_toc(self, pdf: ExportPDF, document: DocumentModel) -> None:
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*BRAND_DARK)
        pdf.cell(0, 12, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        for heading in document.headings:
            indent = "    " * (heading.level - 1) if heading.level > 1 else ""
            pdf.set_font("Helvetica", "B" if heading.level == 1 else "", 11)
            pdf.set_text_color(*BRAND_DARK if heading.level <= 2 else TEXT_COLOR)
            pdf.cell(0, 7, f"{indent}{heading.text}", new_x="LMARGIN", new_y="NEXT")

    def _add_introduction(self, pdf: ExportPDF, document: DocumentModel) -> None:
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*BRAND_DARK)
        pdf.cell(0, 12, "Introduction", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        self._add_text_content(pdf, document.introduction)

    def _add_section(self, pdf: ExportPDF, section: Any) -> None:
        tag = section.heading_tag or "h2"
        level = int(tag[1]) if tag.startswith("h") else 2
        font_size = {1: 18, 2: 15, 3: 13, 4: 12}.get(level, 11)

        pdf.set_font("Helvetica", "B", font_size)
        pdf.set_text_color(*BRAND_DARK)
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.cell(0, font_size + 4, section.heading, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        if section.content:
            self._add_text_content(pdf, section.content)

        for sub in section.subsections:
            sub_level = min(level + 1, 6)
            sub_size = {1: 15, 2: 13, 3: 12, 4: 11}.get(sub_level, 11)
            pdf.set_font("Helvetica", "B", sub_size)
            pdf.set_text_color(*BRAND_ACCENT)
            pdf.cell(0, sub_size + 3, sub.heading, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            if sub.content:
                self._add_text_content(pdf, sub.content)

    def _add_faq(self, pdf: ExportPDF, document: DocumentModel) -> None:
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*BRAND_DARK)
        pdf.cell(0, 12, "Frequently Asked Questions", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        for faq in document.faq:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*BRAND_DARK)
            pdf.multi_cell(0, 6, faq.question)
            pdf.ln(1)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*TEXT_COLOR)
            self._add_text_content(pdf, faq.answer)
            pdf.ln(3)

    def _add_conclusion(self, pdf: ExportPDF, document: DocumentModel) -> None:
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*BRAND_DARK)
        pdf.cell(0, 12, "Conclusion", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        self._add_text_content(pdf, document.conclusion)

    def _add_cta(self, pdf: ExportPDF, document: DocumentModel) -> None:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*BRAND_GREEN)
        pdf.multi_cell(0, 8, document.call_to_action)
        pdf.ln(3)

    def _add_references(self, pdf: ExportPDF, document: DocumentModel) -> None:
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*BRAND_DARK)
        pdf.cell(0, 12, "References", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        for i, ref in enumerate(document.references, 1):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*TEXT_COLOR)
            pdf.cell(0, 6, f"{i}. {ref.label}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(37, 99, 235)
            pdf.cell(0, 5, f"   {ref.url}", new_x="LMARGIN", new_y="NEXT")

    def _add_text_content(self, pdf: ExportPDF, content: str) -> None:
        blocks = content.split("\n\n")
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("```"):
                    pdf._in_code_block = not pdf._in_code_block
                    continue

                if pdf._in_code_block:
                    pdf.set_font("Courier", "", 9)
                    pdf.set_text_color(*BRAND_DARK)
                    x = pdf.get_x()
                    y = pdf.get_y()
                    if y > 260:
                        pdf.add_page()
                        y = pdf.get_y()
                    pdf.set_fill_color(243, 244, 246)
                    pdf.cell(0, 5, f"  {line}", new_x="LMARGIN", new_y="NEXT", fill=True)
                    continue

                if line.startswith("- ") or line.startswith("* "):
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(*TEXT_COLOR)
                    pdf.cell(5)
                    pdf.multi_cell(0, 5, f"• {line[2:]}")
                    continue

                if re.match(r"^\d+\.\s", line):
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(*TEXT_COLOR)
                    pdf.cell(5)
                    pdf.multi_cell(0, 5, f"{line}")
                    continue

                if line.startswith(">"):
                    pdf.set_font("Helvetica", "I", 10)
                    pdf.set_text_color(*MUTED_COLOR)
                    x = pdf.get_x()
                    pdf.set_fill_color(*BG_LIGHT)
                    pdf.multi_cell(0, 5, line.lstrip("> ").strip(), fill=True)
                    pdf.ln(2)
                    continue

                if line.startswith("|"):
                    continue

                text = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
                text = re.sub(r"\*(.+?)\*", r"\1", text)
                text = re.sub(r"`(.+?)`", r"\1", text)
                text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)

                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*TEXT_COLOR)
                pdf.multi_cell(0, 5, text)
                pdf.ln(1)

            pdf.ln(2)

    @staticmethod
    def _size_display(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
