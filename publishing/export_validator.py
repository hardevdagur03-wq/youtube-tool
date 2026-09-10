from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from publishing.models import (
    CodeBlockInfo, DocumentModel, ExportFileInfo, ExportFormat, ImageInfo,
    LinkInfo, ValidationResult, ValidationSeverity,
)

logger = logging.getLogger(__name__)

HTML_TAG_RE = re.compile(r"<(/?)(\w+)[^>]*>")
HEADING_HIERARCHY_RE = re.compile(r"^(#{1,6})\s")
MARKDOWN_FORMATTING_RE = re.compile(r"(\*{1,3}|_{1,3}|~~|`{1,3})")


class ExportValidator:
    def __init__(self, strict: bool = False):
        self.strict = strict

    def validate_document(self, document: DocumentModel) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        results.extend(self._validate_links(document.links))
        results.extend(self._validate_images(document.images))
        results.extend(self._validate_content(document.content))
        results.extend(self._validate_headings(document.headings_text))
        results.extend(self._validate_sections(document.sections))
        results.extend(self._validate_metadata(document))
        results.extend(self._validate_code_blocks(document.code_blocks))
        results.extend(self._validate_table_data(document))

        return results

    def validate_export_file(self, file_path: Path, fmt: ExportFormat) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        if not file_path.exists():
            results.append(ValidationResult(
                check="file_exists",
                severity=ValidationSeverity.ERROR,
                message=f"File not found: {file_path}",
                context={"path": str(file_path), "format": fmt.value},
            ))
            return results

        size_ok = self._validate_file_size(file_path, fmt)
        if size_ok:
            results.append(size_ok)

        content_valid = self._validate_file_content(file_path, fmt)
        if content_valid:
            results.extend(content_valid)

        return results

    def validate_zip(self, zip_path: Path) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        if not zip_path.exists():
            results.append(ValidationResult(
                check="zip_exists",
                severity=ValidationSeverity.ERROR,
                message="ZIP file does not exist",
                context={"path": str(zip_path)},
            ))
            return results

        import zipfile
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                bad = zf.testzip()
                if bad:
                    results.append(ValidationResult(
                        check="zip_integrity",
                        severity=ValidationSeverity.ERROR,
                        message=f"Corrupted file in ZIP: {bad}",
                        context={"corrupted": bad},
                    ))
        except zipfile.BadZipFile:
            results.append(ValidationResult(
                check="zip_integrity",
                severity=ValidationSeverity.ERROR,
                message="Bad ZIP file",
            ))

        return results

    def validate_checksum(self, file_path: Path, expected_checksum: str) -> ValidationResult | None:
        if not file_path.exists():
            return ValidationResult(
                check="checksum",
                severity=ValidationSeverity.ERROR,
                message="File not found for checksum validation",
                context={"path": str(file_path)},
            )
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()[:32]
        if actual != expected_checksum:
            return ValidationResult(
                check="checksum",
                severity=ValidationSeverity.ERROR,
                message=f"Checksum mismatch: expected {expected_checksum}, got {actual}",
                context={"expected": expected_checksum, "actual": actual},
            )
        return None

    def _validate_links(self, links: list[LinkInfo]) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for link in links:
            if not link.url or link.url.strip() == "":
                results.append(ValidationResult(
                    check="link_empty",
                    severity=ValidationSeverity.WARNING if not self.strict else ValidationSeverity.ERROR,
                    message=f"Empty link URL for text: {link.text[:50] if link.text else 'N/A'}",
                ))
            elif link.url.startswith("#"):
                pass
            elif link.url.startswith("http") and not link.url.startswith(("http://", "https://")):
                results.append(ValidationResult(
                    check="link_malformed",
                    severity=ValidationSeverity.ERROR,
                    message=f"Malformed link URL: {link.url[:80]}",
                ))
        return results

    def _validate_images(self, images: list[ImageInfo]) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for img in images:
            if not img.url:
                results.append(ValidationResult(
                    check="image_no_url",
                    severity=ValidationSeverity.ERROR,
                    message=f"Image missing URL: alt='{img.alt[:50] if img.alt else 'N/A'}'",
                ))
        return results

    def _validate_content(self, content: str | None) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        if not content or not content.strip():
            results.append(ValidationResult(
                check="content_empty",
                severity=ValidationSeverity.ERROR,
                message="Document content is empty",
            ))
            return results

        unclosed = self._check_unclosed_tags(content)
        for tag in unclosed:
            results.append(ValidationResult(
                check="unclosed_tag",
                severity=ValidationSeverity.WARNING,
                message=f"Possibly unclosed HTML tag: <{tag}>",
                context={"tag": tag},
            ))

        return results

    def _validate_headings(self, headings: list[str]) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        if not headings:
            return results

        prev_level = 1
        for h in headings:
            m = HEADING_HIERARCHY_RE.match(h)
            if m:
                level = len(m.group(1))
                if level > prev_level + 1:
                    results.append(ValidationResult(
                        check="heading_skip",
                        severity=ValidationSeverity.WARNING,
                        message=f"Heading level skips from {prev_level} to {level}: '{h.strip()}'",
                    ))
                prev_level = level
        return results

    def _validate_sections(self, sections: Any) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        if not sections:
            results.append(ValidationResult(
                check="no_sections",
                severity=ValidationSeverity.ERROR,
                message="Document has no sections",
            ))
        return results

    def _validate_metadata(self, document: DocumentModel) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        if not document.title:
            results.append(ValidationResult(
                check="title_missing",
                severity=ValidationSeverity.ERROR,
                message="Document title is missing",
            ))
        if document.meta_description and len(document.meta_description) > 320:
            results.append(ValidationResult(
                check="meta_description_long",
                severity=ValidationSeverity.WARNING,
                message=f"Meta description too long: {len(document.meta_description)} chars (max 320)",
            ))
        return results

    def _validate_code_blocks(self, blocks: list[CodeBlockInfo]) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for block in blocks:
            if not block.language:
                results.append(ValidationResult(
                    check="code_language_missing",
                    severity=ValidationSeverity.WARNING,
                    message="Code block without language specification",
                ))
        return results

    def _validate_table_data(self, document: DocumentModel) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for table in document.tables:
            if not table.headers and not table.rows:
                results.append(ValidationResult(
                    check="table_empty",
                    severity=ValidationSeverity.WARNING,
                    message=f"Empty table: '{table.caption[:50] if table.caption else 'N/A'}'",
                ))
        return results

    def _check_unclosed_tags(self, content: str) -> list[str]:
        stack: list[str] = []
        for m in HTML_TAG_RE.finditer(content):
            is_closing = bool(m.group(1))
            tag = m.group(2).lower()
            if tag in {"br", "hr", "img", "input", "meta", "link", "area", "base", "col",
                        "embed", "source", "track", "wbr", "!DOCTYPE", "!--"}:
                continue
            if is_closing:
                if stack and stack[-1] == tag:
                    stack.pop()
            else:
                stack.append(tag)
        return stack

    def _validate_file_size(self, file_path: Path, fmt: ExportFormat) -> ValidationResult | None:
        size = file_path.stat().st_size
        if size == 0:
            return ValidationResult(
                check="file_empty",
                severity=ValidationSeverity.ERROR,
                message=f"Empty export file: {file_path.name}",
                context={"format": fmt.value, "path": str(file_path)},
            )
        return None

    def _validate_file_content(self, file_path: Path, fmt: ExportFormat) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        suffix = file_path.suffix.lower()

        if suffix in {".html", ".htm"}:
            content = file_path.read_text(encoding="utf-8")
            unclosed = self._check_unclosed_tags(content)
            for tag in unclosed:
                results.append(ValidationResult(
                    check="html_unclosed_tag",
                    severity=ValidationSeverity.WARNING,
                    message=f"HTML file has unclosed tag: <{tag}>",
                    context={"file": file_path.name, "tag": tag},
                ))

            if "<!DOCTYPE html>" not in content and "<!doctype html>" not in content:
                results.append(ValidationResult(
                    check="html_no_doctype",
                    severity=ValidationSeverity.WARNING,
                    message="HTML file missing DOCTYPE declaration",
                ))

        elif suffix == ".json":
            content = file_path.read_text(encoding="utf-8")
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                results.append(ValidationResult(
                    check="json_invalid",
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid JSON: {e}",
                ))

        elif suffix == ".md":
            content = file_path.read_text(encoding="utf-8")
            unclosed_code = content.count("```")
            if unclosed_code % 2 != 0:
                results.append(ValidationResult(
                    check="markdown_unclosed_code",
                    severity=ValidationSeverity.WARNING,
                    message=f"Unclosed code block markers ({unclosed_code} backtick triples)",
                ))

        return results
