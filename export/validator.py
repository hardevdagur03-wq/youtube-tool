"""Export Validator — Phase 10.

Validates exported files for integrity, encoding, and structure.
"""

from __future__ import annotations
from pathlib import Path

from models.blog_export import ExportFile


class ExportValidator:
    """Validates exported files."""

    MIN_SIZE = 50  # bytes

    def validate(self, filepath: Path, export_file: ExportFile) -> ExportFile:
        if not filepath.exists():
            export_file.valid = False
            export_file.validation_message = "File does not exist"
            return export_file

        if filepath.stat().st_size == 0:
            export_file.valid = False
            export_file.validation_message = "File is empty"
            return export_file

        if filepath.stat().st_size < self.MIN_SIZE:
            export_file.valid = False
            export_file.validation_message = f"File too small ({filepath.stat().st_size} bytes)"
            return export_file

        # Format-specific checks
        fmt = export_file.format
        ext = filepath.suffix.lower()

        if fmt == "markdown" and ext == ".md":
            valid, msg = self._validate_markdown(filepath)
            if not valid:
                export_file.valid = False
                export_file.validation_message = msg

        elif fmt == "html" and ext == ".html":
            valid, msg = self._validate_html(filepath)
            if not valid:
                export_file.valid = False
                export_file.validation_message = msg

        elif fmt == "docx" and ext == ".docx":
            valid, msg = self._validate_docx(filepath)
            if not valid:
                export_file.valid = False
                export_file.validation_message = msg

        elif fmt == "pdf" and ext == ".pdf":
            valid, msg = self._validate_pdf(filepath)
            if not valid:
                export_file.valid = False
                export_file.validation_message = msg

        return export_file

    def _validate_markdown(self, path: Path) -> tuple[bool, str]:
        try:
            content = path.read_text(encoding="utf-8")
            if not content.strip():
                return False, "Markdown file is empty"
            if len(content) < 20:
                return False, "Markdown content too short"
            # Check for basic markdown structure
            if not content.startswith("#"):
                return False, "Markdown missing H1 heading"
            return True, ""
        except UnicodeDecodeError:
            return False, "Markdown file has invalid encoding"
        except Exception as exc:
            return False, f"Markdown validation error: {exc}"

    def _validate_html(self, path: Path) -> tuple[bool, str]:
        try:
            content = path.read_text(encoding="utf-8")
            if "<!DOCTYPE html>" not in content and "<html" not in content:
                return False, "HTML missing DOCTYPE or html tag"
            if "<title>" not in content:
                return False, "HTML missing title tag"
            if "<meta name=\"description\"" not in content:
                return False, "HTML missing meta description"
            if "</article>" not in content and "</body>" not in content:
                return False, "HTML missing closing tags"
            return True, ""
        except Exception as exc:
            return False, f"HTML validation error: {exc}"

    def _validate_docx(self, path: Path) -> tuple[bool, str]:
        try:
            from docx import Document
            doc = Document(str(path))
            if len(doc.paragraphs) == 0:
                return False, "DOCX has no paragraphs"
            return True, ""
        except Exception as exc:
            return False, f"DOCX validation error: {exc}"

    def _validate_pdf(self, path: Path) -> tuple[bool, str]:
        try:
            content = path.read_bytes()
            if not content.startswith(b'%PDF'):
                return False, "PDF magic bytes missing"
            if len(content) < 1000:
                return False, "PDF file too small"
            return True, ""
        except Exception as exc:
            return False, f"PDF validation error: {exc}"
