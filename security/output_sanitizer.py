from __future__ import annotations

import html
import json
import re
from typing import Any

import bleach


class OutputSanitizer:
    ALLOWED_HTML_TAGS = [
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "br", "hr",
        "ul", "ol", "li",
        "strong", "em", "u", "s", "sub", "sup",
        "a", "code", "pre", "blockquote",
        "table", "thead", "tbody", "tr", "th", "td",
        "img", "figure", "figcaption",
        "div", "span",
    ]

    ALLOWED_HTML_ATTRIBUTES = {
        "a": ["href", "title", "rel", "target"],
        "img": ["src", "alt", "title", "width", "height"],
        "*": ["class", "id", "style"],
    }

    ALLOWED_URL_SCHEMES = ["http", "https", "mailto"]

    def sanitize_html(self, content: str) -> str:
        return bleach.clean(
            content,
            tags=self.ALLOWED_HTML_TAGS,
            attributes=self.ALLOWED_HTML_ATTRIBUTES,
            protocols=self.ALLOWED_URL_SCHEMES,
            strip=True,
        )

    def sanitize_markdown(self, content: str) -> str:
        sanitized = content
        sanitized = re.sub(r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r"!\[.*?\]\(.*?\)", "", sanitized)
        sanitized = re.sub(r"\[.*?\]\(.*?\)", lambda m: m.group(0).split("](")[0] + "]", sanitized)
        return sanitized

    def sanitize_json(self, data: Any, depth: int = 0) -> Any:
        if depth > 10:
            return str(data)[:100]
        if isinstance(data, str):
            return data[:10000]
        if isinstance(data, dict):
            return {k: self.sanitize_json(v, depth + 1) for k, v in data.items()}
        if isinstance(data, list):
            return [self.sanitize_json(v, depth + 1) for v in data[:1000]]
        return data

    def sanitize_error_message(self, message: str) -> str:
        sanitized = message
        sanitized = re.sub(r"(api[_-]?key|secret|password|token|auth)[=:]\s*\S+", r"\1=***", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"(-----BEGIN.*?-----.*?-----END.*?-----)", "[REDACTED CERTIFICATE]", sanitized, flags=re.DOTALL)
        sanitized = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", sanitized)
        sanitized = re.sub(r"\b(\d{3}-\d{2,4}-\d{4})\b", "[SSN]", sanitized)
        sanitized = self.sanitize_html(sanitized)
        return sanitized[:2000]

    def sanitize_filename(self, filename: str) -> str:
        sanitized = re.sub(r"[<>:\"/\\|?*]", "_", filename)
        sanitized = re.sub(r"\.{2,}", ".", sanitized)
        sanitized = re.sub(r"\s+", "_", sanitized)
        return sanitized.strip("._")

    def sanitize_log_output(self, log_data: dict[str, Any]) -> dict[str, Any]:
        sensitive_keys = {"password", "secret", "token", "api_key", "api_key", "access_key", "private_key", "auth"}
        result = {}
        for k, v in log_data.items():
            if any(s in k.lower() for s in sensitive_keys):
                result[k] = "***REDACTED***"
            elif isinstance(v, str):
                result[k] = v[:500]
            else:
                result[k] = v
        return result
