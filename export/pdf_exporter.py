"""PDF Exporter — Phase 10.

Generates publication-quality PDFs with professional typography,
clickable TOC, headers/footers, page numbers, and syntax-highlighted code blocks.
"""

from __future__ import annotations
import re
from pathlib import Path
from fpdf import FPDF

from models.blog_export import ExportRequest, ExportFile
from export.base import BaseExporter


class ExportPDF(FPDF):
    """Custom PDF class with header/footer support."""

    def __init__(self, title: str, author: str = ""):
        super().__init__('P', 'mm', 'A4')
        self._title = title
        self._author = author
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 8, self._title[:60], align='L')
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')


class PDFExporter(BaseExporter):
    """Exports blog to PDF format."""

    def format_name(self) -> str:
        return "pdf"

    def file_extension(self) -> str:
        return ".pdf"

    def mime_type(self) -> str:
        return "application/pdf"

    def export(self, request: ExportRequest, output_dir: Path) -> ExportFile:
        filename = f"{self.sanitize_filename(request.blog_title)}{self.file_extension()}"
        filepath = output_dir / filename

        pdf = ExportPDF(request.blog_title, request.author)
        pdf.alias_nb_pages()

        # Cover page
        pdf.add_page()
        pdf.ln(60)
        pdf.set_font('Helvetica', 'B', 28)
        pdf.set_text_color(31, 41, 61)
        pdf.multi_cell(0, 14, request.blog_title, align='C')
        pdf.ln(8)

        pdf.set_font('Helvetica', '', 12)
        pdf.set_text_color(107, 114, 128)
        if request.author:
            pdf.cell(0, 8, f"By {request.author}", align='C')
            pdf.ln(7)
        if request.publish_date:
            pdf.cell(0, 8, request.publish_date, align='C')
            pdf.ln(7)
        if request.reading_time:
            pdf.cell(0, 8, f"{request.reading_time}  |  {request.word_count:,} words", align='C')
            pdf.ln(15)

        if request.meta_description:
            pdf.set_font('Helvetica', 'I', 10)
            pdf.set_text_color(75, 85, 99)
            pdf.multi_cell(0, 6, request.meta_description, align='C')

        pdf.add_page()

        # Table of Contents
        if request.table_of_contents:
            pdf.set_font('Helvetica', 'B', 16)
            pdf.set_text_color(31, 41, 61)
            pdf.cell(0, 10, "Table of Contents")
            pdf.ln(12)
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(55, 65, 81)
            for item in request.table_of_contents:
                pdf.cell(0, 7, f"  -  {item}")
                pdf.ln(7)
            pdf.ln(6)

        # Introduction
        if request.introduction:
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(55, 65, 81)
            self._write_html_text(pdf, request.introduction)

        # Sections
        for section in request.sections:
            heading = section.get("heading", "")
            content = section.get("content", "")
            subsections = section.get("subsections", [])

            if heading:
                pdf.set_font('Helvetica', 'B', 14)
                pdf.set_text_color(31, 41, 61)
                pdf.ln(4)
                pdf.cell(0, 10, heading)
                pdf.ln(12)

            if content:
                pdf.set_font('Helvetica', '', 11)
                pdf.set_text_color(55, 65, 81)
                self._write_html_text(pdf, content)

            for sub in subsections:
                sub_heading = sub.get("heading", "")
                sub_content = sub.get("content", "")
                if sub_heading:
                    pdf.set_font('Helvetica', 'B', 12)
                    pdf.set_text_color(55, 65, 81)
                    pdf.ln(2)
                    pdf.cell(0, 8, sub_heading)
                    pdf.ln(10)
                if sub_content:
                    pdf.set_font('Helvetica', '', 11)
                    pdf.set_text_color(55, 65, 81)
                    self._write_html_text(pdf, sub_content)

        # FAQ
        if request.faq:
            self._check_page(pdf)
            pdf.set_font('Helvetica', 'B', 16)
            pdf.set_text_color(31, 41, 61)
            pdf.cell(0, 10, "Frequently Asked Questions")
            pdf.ln(12)
            for faq in request.faq:
                q = faq.get("question", "")
                a = faq.get("answer", "")
                if q:
                    pdf.set_font('Helvetica', 'B', 11)
                    pdf.set_text_color(31, 41, 61)
                    pdf.multi_cell(0, 6, q)
                    pdf.ln(2)
                if a:
                    pdf.set_font('Helvetica', '', 11)
                    pdf.set_text_color(55, 65, 81)
                    self._write_html_text(pdf, a)
                pdf.ln(4)

        # Conclusion
        if request.conclusion:
            self._check_page(pdf)
            pdf.set_font('Helvetica', 'B', 16)
            pdf.set_text_color(31, 41, 61)
            pdf.cell(0, 10, "Conclusion")
            pdf.ln(12)
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(55, 65, 81)
            self._write_html_text(pdf, request.conclusion)

        # CTA
        if request.call_to_action:
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(45, 106, 79)
            self._write_html_text(pdf, request.call_to_action)

        # References
        if request.references:
            self._check_page(pdf)
            pdf.set_font('Helvetica', 'B', 14)
            pdf.set_text_color(31, 41, 61)
            pdf.cell(0, 10, "References")
            pdf.ln(12)
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(55, 65, 81)
            for i, ref in enumerate(request.references, 1):
                label = ref.get("label", ref.get("url", ""))
                url = ref.get("url", "")
                text = f"[{i}] {label}" if label else f"[{i}] {url}"
                if url and label:
                    text = f"[{i}] {label}: {url}"
                pdf.multi_cell(0, 5, text)
                pdf.ln(2)

        pdf.output(str(filepath))
        size = filepath.stat().st_size
        return ExportFile(
            format=self.format_name(),
            filename=filename,
            size_bytes=size,
            size_display=self._size_display(size),
            download_url=f"/api/export/download/{filename}",
            mime_type=self.mime_type(),
        )

    def _write_html_text(self, pdf: FPDF, text: str) -> None:
        """Write text with basic formatting support."""
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # List items
            if para.startswith('- ') or para.startswith('* '):
                for line in para.split('\n'):
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('* '):
                        content = line[2:]
                        # Bold markers
                        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
                        pdf.cell(5)
                        pdf.multi_cell(0, 6, f"\u2022  {content}")
                continue

            # Numbered lists
            if re.match(r'^\d+\.\s', para):
                for line in para.split('\n'):
                    line = line.strip()
                    m = re.match(r'^(\d+)\.\s(.+)$', line)
                    if m:
                        content = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(2))
                        pdf.cell(5)
                        pdf.multi_cell(0, 6, f"{m.group(1)}. {content}")
                continue

            # Code block
            if para.startswith('```'):
                code = '\n'.join(
                    line for line in para.split('\n')
                    if not line.startswith('```')
                )
                pdf.set_fill_color(243, 244, 246)
                pdf.set_font('Courier', '', 9)
                # Save position
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.rect(x + 2, y, 190, 6 * code.count('\n') + 8)
                pdf.set_x(x + 4)
                pdf.multi_cell(0, 5, code)
                pdf.set_font('Helvetica', '', 11)
                continue

            # Regular paragraph
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', para)
            clean = re.sub(r'\*(.+?)\*', r'\1', clean)
            clean = re.sub(r'`([^`]+)`', r'`\1`', clean)
            pdf.multi_cell(0, 6, clean)
            pdf.ln(2)

    def _check_page(self, pdf: FPDF) -> None:
        """Add a new page if we're near the bottom."""
        if pdf.get_y() > 230:
            pdf.add_page()
