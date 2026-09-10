"""UUID Manager — generates UUIDs, short IDs, and safe folder names.

No existing code is modified.
"""

from __future__ import annotations

import hashlib
import re
import uuid


class UUIDManager:
    """Generates and validates unique identifiers for projects."""

    @staticmethod
    def generate_uuid() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def generate_short_id(length: int = 8) -> str:
        return uuid.uuid4().hex[:length]

    @staticmethod
    def generate_project_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def generate_checkpoint_id() -> str:
        return f"cp_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def generate_version_id() -> str:
        return f"v_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def generate_history_id() -> str:
        return f"ev_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def safe_folder_name(name: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        safe = re.sub(r"_+", "_", safe).strip("_")
        if not safe:
            safe = "project"
        if len(safe) > 64:
            safe = safe[:64]
        return safe.lower()

    @staticmethod
    def generate_folder_name(project_id: str, video_id: str = "") -> str:
        if video_id:
            return f"{project_id[:12]}_{video_id}"
        return project_id[:16]

    @staticmethod
    def checksum(data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    @staticmethod
    def validate_uuid(value: str) -> bool:
        try:
            uuid.UUID(hex=value)
            return True
        except (ValueError, AttributeError):
            return False
