from __future__ import annotations

import json
import re
from typing import Any

from security.security_models import ThreatDetectedError, ThreatType


class InputValidator:
    MAX_STRING_LENGTH = 10000
    MAX_JSON_SIZE = 1024 * 1024
    MAX_LIST_ITEMS = 1000

    SQL_INJECTION_PATTERNS: list[re.Pattern] = [
        re.compile(r"(\bSELECT\b.*\bFROM\b)", re.IGNORECASE),
        re.compile(r"(\bDROP\b.*\bTABLE\b)", re.IGNORECASE),
        re.compile(r"(\bINSERT\b.*\bINTO\b)", re.IGNORECASE),
        re.compile(r"(\bDELETE\b.*\bFROM\b)", re.IGNORECASE),
        re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),
        re.compile(r"(\bALTER\b.*\bTABLE\b)", re.IGNORECASE),
        re.compile(r"(\bEXEC\b|\bEXECUTE\b)", re.IGNORECASE),
        re.compile(r"(\bOR\s+1\s*=\s*1\b)", re.IGNORECASE),
        re.compile(r"'?\s*(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?", re.IGNORECASE),
        re.compile(r"(--|#|/\*).*", re.IGNORECASE),
    ]

    XSS_PATTERNS: list[re.Pattern] = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
        re.compile(r"<[^>]*\bon\w+\s*=", re.IGNORECASE),
        re.compile(r"<iframe[^>]*>", re.IGNORECASE),
        re.compile(r"<embed[^>]*>", re.IGNORECASE),
        re.compile(r"<object[^>]*>", re.IGNORECASE),
        re.compile(r"document\.(cookie|location|write)", re.IGNORECASE),
        re.compile(r"eval\s*\(", re.IGNORECASE),
        re.compile(r"<[^>]*style\s*=\s*['\"][^'\"]*expression\s*\(", re.IGNORECASE),
    ]

    PATH_TRAVERSAL_PATTERNS: list[re.Pattern] = [
        re.compile(r"\.\."),
        re.compile(r"~"),
        re.compile(r"^/"),
        re.compile(r"[<>|:;&]"),
    ]

    YOUTUBE_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
    YOUTUBE_URL_PATTERN = re.compile(
        r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/",
        re.IGNORECASE,
    )
    EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def validate_string(self, value: str, field_name: str = "field", max_length: int | None = None) -> str:
        if not isinstance(value, str):
            raise ThreatDetectedError(f"{field_name} must be a string", ThreatType.XSS)
        max_len = max_length or self.MAX_STRING_LENGTH
        if len(value) > max_len:
            raise ThreatDetectedError(
                f"{field_name} exceeds max length {max_len}", ThreatType.API_ABUSE
            )
        return value

    def validate_json(self, data: str | bytes, max_size: int | None = None) -> Any:
        size = max_size or self.MAX_JSON_SIZE
        raw = data if isinstance(data, bytes) else data.encode()
        if len(raw) > size:
            raise ThreatDetectedError("JSON payload exceeds max size", ThreatType.API_ABUSE)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ThreatDetectedError(f"Invalid JSON: {e}", ThreatType.API_ABUSE)

    def check_sql_injection(self, value: str) -> str:
        for pattern in self.SQL_INJECTION_PATTERNS:
            if pattern.search(value):
                raise ThreatDetectedError(
                    "Potential SQL injection detected", ThreatType.SQL_INJECTION
                )
        return value

    def check_xss(self, value: str) -> str:
        for pattern in self.XSS_PATTERNS:
            if pattern.search(value):
                raise ThreatDetectedError(
                    "Potential XSS detected", ThreatType.XSS
                )
        return value

    def check_path_traversal(self, value: str) -> str:
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(value):
                raise ThreatDetectedError(
                    "Potential path traversal detected", ThreatType.PATH_TRAVERSAL
                )
        return value

    def validate_video_id(self, video_id: str) -> str:
        self.validate_string(video_id, "video_id", 50)
        if not self.YOUTUBE_VIDEO_ID_PATTERN.match(video_id):
            raise ThreatDetectedError("Invalid YouTube video ID format", ThreatType.API_ABUSE)
        return video_id

    def validate_email(self, email: str) -> str:
        self.validate_string(email, "email", 254)
        if not self.EMAIL_PATTERN.match(email):
            raise ThreatDetectedError("Invalid email format", ThreatType.API_ABUSE)
        return email

    def validate_url(self, url: str) -> str:
        self.validate_string(url, "url", 2048)
        self.check_xss(url)
        self.check_path_traversal(url)
        return url

    def sanitize_input(self, value: str) -> str:
        if not isinstance(value, str):
            return str(value)
        value = self.check_sql_injection(value)
        value = self.check_xss(value)
        value = self.check_path_traversal(value)
        return value

    def validate_list(self, items: list[Any], max_items: int | None = None) -> list[Any]:
        max_i = max_items or self.MAX_LIST_ITEMS
        if len(items) > max_i:
            raise ThreatDetectedError(
                f"List exceeds max items {max_i}", ThreatType.API_ABUSE
            )
        return items
