"""Export Provider abstraction — common interface for all export formats.

Every export format (Markdown, HTML, DOCX, PDF, JSON, CSV) implements
this contract. Business logic never generates files directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"


@dataclass
class ExportRequest:
    title: str = ""
    content: str = ""
    author: str = ""
    format: ExportFormat = ExportFormat.MARKDOWN
    include_toc: bool = False
    include_meta: bool = True
    template: str = ""
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    success: bool = False
    format: str = ""
    file_path: str = ""
    file_size_bytes: int = 0
    error: str = ""
    content: str = ""


class ExportProvider(ABC):
    """Abstract interface for export format implementations.

    All exporters (Markdown, HTML, DOCX, PDF, etc.) implement this.
    """

    @property
    @abstractmethod
    def format_name(self) -> str:
        ...

    @abstractmethod
    def export(self, request: ExportRequest) -> ExportResult:
        ...

    @abstractmethod
    def validate(self, content: str) -> bool:
        ...


class MarkdownExportProvider(ExportProvider):
    """Export to Markdown format."""

    @property
    def format_name(self) -> str:
        return "markdown"

    def export(self, request: ExportRequest) -> ExportResult:
        content = request.content
        if request.include_toc:
            toc = self._generate_toc(content)
            content = toc + "\n\n" + content
        if request.include_meta:
            meta = (
                f"---\ntitle: {request.title}\n"
                f"author: {request.author or 'unknown'}\n"
                f"---\n\n"
            )
            content = meta + content
        return ExportResult(
            success=True,
            format="markdown",
            content=content,
            file_size_bytes=len(content.encode("utf-8")),
        )

    def validate(self, content: str) -> bool:
        return bool(content and content.strip())

    def _generate_toc(self, content: str) -> str:
        lines = []
        for line in content.split("\n"):
            if line.startswith("## "):
                level = line.count("#")
                title = line.strip("# ")
                indent = "  " * (level - 1)
                slug = title.lower().replace(" ", "-").replace(".", "")
                lines.append(f"{indent}- [{title}](#{slug})")
            elif line.startswith("# ") and len(lines) == 0:
                title = line.strip("# ")
                slug = title.lower().replace(" ", "-").replace(".", "")
                lines.append(f"- [{title}](#{slug})")
        return "\n".join(lines) if lines else ""


class HTMLExportProvider(ExportProvider):
    """Export to HTML format."""

    @property
    def format_name(self) -> str:
        return "html"

    def export(self, request: ExportRequest) -> ExportResult:
        import html as html_mod

        content_parts = ["<!DOCTYPE html>", '<html lang="en">', "<head>", "<meta charset='UTF-8'>"]
        if request.title:
            content_parts.append(f"<title>{html_mod.escape(request.title)}</title>")
        content_parts.append("<style>body{max-width:800px;margin:0 auto;padding:20px;line-height:1.6}")
        content_parts.append("h1,h2,h3{color:#333}img{max-width:100%}code{background:#f4f4f4;padding:2px 6px}")
        content_parts.append("pre{background:#f4f4f4;padding:16px;overflow-x:auto}</style>")
        content_parts.append("</head><body>")
        if request.title:
            content_parts.append(f"<h1>{html_mod.escape(request.title)}</h1>")
        for line in request.content.split("\n"):
            if line.startswith("## "):
                content_parts.append(f"<h2>{html_mod.escape(line[3:])}</h2>")
            elif line.startswith("### "):
                content_parts.append(f"<h3>{html_mod.escape(line[4:])}</h3>")
            elif line.startswith("```"):
                pass
            elif line.strip():
                content_parts.append(f"<p>{html_mod.escape(line)}</p>")
        content_parts.append("</body></html>")

        content = "\n".join(content_parts)
        return ExportResult(
            success=True,
            format="html",
            content=content,
            file_size_bytes=len(content.encode("utf-8")),
        )

    def validate(self, content: str) -> bool:
        return bool(content and content.strip())


class JSONExportProvider(ExportProvider):
    """Export to JSON format."""

    @property
    def format_name(self) -> str:
        return "json"

    def export(self, request: ExportRequest) -> ExportResult:
        import json
        data = {
            "title": request.title,
            "author": request.author,
            "content": request.content,
        }
        if request.options:
            data["metadata"] = request.options
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return ExportResult(
            success=True,
            format="json",
            content=content,
            file_size_bytes=len(content.encode("utf-8")),
        )

    def validate(self, content: str) -> bool:
        import json
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, ValueError):
            return False


class CSVExportProvider(ExportProvider):
    """Export to CSV format."""

    @property
    def format_name(self) -> str:
        return "csv"

    def export(self, request: ExportRequest) -> ExportResult:
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        rows = request.options.get("rows", [])
        headers = request.options.get("headers", ["Key", "Value"])
        if headers:
            writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        content = output.getvalue()
        return ExportResult(
            success=True,
            format="csv",
            content=content,
            file_size_bytes=len(content.encode("utf-8")),
        )

    def validate(self, content: str) -> bool:
        return bool(content and content.strip())


class MockExportProvider(ExportProvider):
    """Mock export provider for testing."""

    def __init__(self, name: str = "mock", fail: bool = False):
        self._name = name
        self._fail = fail

    @property
    def format_name(self) -> str:
        return self._name

    def export(self, request: ExportRequest) -> ExportResult:
        if self._fail:
            return ExportResult(success=False, format=self._name, error="Export failed")
        return ExportResult(
            success=True,
            format=self._name,
            content=request.content,
            file_size_bytes=len(request.content.encode("utf-8")),
        )

    def validate(self, content: str) -> bool:
        return not self._fail and bool(content)
