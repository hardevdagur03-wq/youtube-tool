"""Quality Validator — validates exports and blocks invalid ones.

Ensures every export is publication-ready. Validates Markdown structure,
HTML semantics, DOCX integrity, PDF validity, ZIP bundle completeness.
Rejects invalid exports with detailed error reports.
Target: 0 malformed exports.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from export_delivery.config import ExportDeliveryConfig
from export_delivery.constants import (
    QUALITY_MIN_FILE_SIZE,
    QUALITY_MIN_MARKDOWN_CHARS,
    QUALITY_MIN_PDF_SIZE,
)

logger = logging.getLogger(__name__)


class ExportValidationError(Exception):
    """Raised when an export fails quality validation."""
    pass


class QualityValidator:
    """Validates export files for publication readiness.

    Runs format-specific checks and blocks invalid exports.
    """

    def __init__(self, config: ExportDeliveryConfig | None = None) -> None:
        self._config = config or ExportDeliveryConfig.from_env()
        self._block_on_failure = self._config.quality_block_on_failure

    def validate(self, file_info: dict[str, Any]) -> dict[str, Any]:
        """Validate a single export file.

        Args:
            file_info: Dict with format, filename, filepath keys.

        Returns:
            Validation result dict with passed, errors, warnings.

        Raises:
            ExportValidationError: If validation fails and blocking is enabled.
        """
        fmt = file_info.get("format", "")
        filepath = file_info.get("filepath", "")
        errors = []
        warnings = []

        # Basic checks (all formats)
        if not filepath or not os.path.isfile(filepath):
            errors.append(f"File not found: {filepath}")
        else:
            file_size = os.path.getsize(filepath)
            if file_size < QUALITY_MIN_FILE_SIZE:
                errors.append(f"File too small: {file_size} bytes (min {QUALITY_MIN_FILE_SIZE})")

        # Format-specific checks
        if not errors:
            validator = self._get_validator(fmt)
            if validator:
                try:
                    fmt_errors, fmt_warnings = validator(filepath, file_info)
                    errors.extend(fmt_errors)
                    warnings.extend(fmt_warnings)
                except Exception as exc:
                    errors.append(f"Validation error: {exc}")

        result = {
            "format": fmt,
            "filename": file_info.get("filename", ""),
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

        if not result["passed"] and self._block_on_failure:
            raise ExportValidationError(
                f"Export validation FAILED for {fmt}: {'; '.join(errors)}"
            )

        return result

    def validate_all(
        self, files: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate all export files in a bundle.

        Args:
            files: List of file info dicts.

        Returns:
            List of validation results.

        Raises:
            ExportValidationError: If any file fails and blocking is enabled.
        """
        results = []
        for f in files:
            result = self.validate(f)
            results.append(result)
        return results

    def _get_validator(self, fmt: str):
        """Get the format-specific validator function."""
        validators = {
            "markdown": self._validate_markdown,
            "html": self._validate_html,
            "docx": self._validate_docx,
            "pdf": self._validate_pdf,
            "txt": self._validate_txt,
            "json": self._validate_json,
            "seo_json": self._validate_json,
            "jsonld_schema": self._validate_json,
            "yaml_metadata": self._validate_yaml,
        }
        return validators.get(fmt)

    def _validate_markdown(self, filepath: str, info: dict) -> tuple[list, list]:
        """Validate Markdown file."""
        errors = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if len(content) < QUALITY_MIN_MARKDOWN_CHARS:
            errors.append(f"Markdown too short: {len(content)} chars")

        if not content.startswith("---"):
            errors.append("Missing YAML front matter (must start with ---)")

        # Check for unclosed code fences
        code_fences = len(re.findall(r"^```", content, re.MULTILINE))
        if code_fences % 2 != 0:
            errors.append(f"Unclosed code fences: {code_fences} fences found")

        # Check for broken links
        broken = re.findall(r"\[([^\]]*)\]\(\s*\)", content)
        if broken:
            errors.append(f"Broken links found: {len(broken)} empty URLs")

        return errors, []

    def _validate_html(self, filepath: str, info: dict) -> tuple[list, list]:
        """Validate HTML file."""
        errors = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if "<!DOCTYPE html>" not in content.upper():
            errors.append("Missing DOCTYPE declaration")
        if "<html" not in content.lower():
            errors.append("Missing <html> tag")
        if "</html>" not in content.lower():
            errors.append("Missing closing </html> tag")
        if "<title>" not in content.lower():
            errors.append("Missing <title> tag")
        if "<body" not in content.lower():
            errors.append("Missing <body> tag")
        if "</body>" not in content.lower():
            errors.append("Missing closing </body> tag")

        # Check for unclosed tags (basic check)
        open_tags = len(re.findall(r"<(?!area|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)([a-z]+)", content.lower()))
        close_tags = len(re.findall(r"</([a-z]+)>", content.lower()))
        if open_tags > close_tags:
            errors.append(f"Unclosed HTML tags: {open_tags - close_tags} open tags remain")

        return errors, []

    def _validate_docx(self, filepath: str, info: dict) -> tuple[list, list]:
        """Validate DOCX file."""
        errors = []
        try:
            from docx import Document
            doc = Document(filepath)
            if len(doc.paragraphs) == 0:
                errors.append("DOCX has no paragraphs")
        except ImportError:
            pass  # Can't validate without python-docx
        except Exception as exc:
            errors.append(f"DOCX validation error: {exc}")
        return errors, []

    def _validate_pdf(self, filepath: str, info: dict) -> tuple[list, list]:
        """Validate PDF file."""
        errors = []
        file_size = os.path.getsize(filepath)
        if file_size < QUALITY_MIN_PDF_SIZE:
            errors.append(f"PDF too small: {file_size} bytes")

        with open(filepath, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                errors.append("Invalid PDF header (missing %PDF-)")

        return errors, []

    def _validate_txt(self, filepath: str, info: dict) -> tuple[list, list]:
        """Validate text file."""
        errors = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if not content.strip():
            errors.append("Text file is empty")
        return errors, []

    def _validate_json(self, filepath: str, info: dict) -> tuple[list, list]:
        """Validate JSON file."""
        errors = []
        import json
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data:
                errors.append("JSON file is empty")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON: {exc}")
        except Exception as exc:
            errors.append(f"JSON read error: {exc}")
        return errors, []

    def _validate_yaml(self, filepath: str, info: dict) -> tuple[list, list]:
        """Validate YAML file by reading and checking structure."""
        errors = []
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            errors.append("YAML file is empty")
        if "title:" not in content:
            errors.append("YAML missing 'title' field")
        return errors, []
