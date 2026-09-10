"""Section Version Manager — maintains version history per section.

Each section keeps its own version chain. Supports rollback.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from typing import Any

from section_generation.section_models import (
    SectionVersion,
    SectionOutput,
    utc_now,
)

logger = logging.getLogger(__name__)


class SectionVersionManager:
    """Version management for individual sections."""

    def __init__(self) -> None:
        self._versions: dict[str, list[SectionVersion]] = {}
        self._lock = threading.Lock()

    def create_version(
        self,
        section_id: str,
        output: SectionOutput,
        prompt: str = "",
        reason: str = "",
    ) -> SectionVersion:
        content_hash = hashlib.sha256(output.content.encode()).hexdigest()[:16]
        with self._lock:
            history = self._versions.get(section_id, [])
            version_number = len(history) + 1

            sv = SectionVersion(
                version_number=version_number,
                created_at=utc_now(),
                content_hash=content_hash,
                content=output.content,
                prompt=prompt,
                validation_score=0.0,
                generation_time_ms=output.generation_time_ms,
                tokens_used=output.tokens_input + output.tokens_output,
                reason=reason or f"version_{version_number}",
            )
            history.append(sv)
            self._versions[section_id] = history
            logger.debug(
                "Version %d created for section %s (hash=%s)",
                version_number, section_id, content_hash,
            )
            return sv

    def get_version(
        self,
        section_id: str,
        version_number: int,
    ) -> SectionVersion | None:
        with self._lock:
            history = self._versions.get(section_id, [])
            for v in history:
                if v.version_number == version_number:
                    return v
            return None

    def get_latest_version(self, section_id: str) -> SectionVersion | None:
        with self._lock:
            history = self._versions.get(section_id, [])
            if not history:
                return None
            return history[-1]

    def get_version_history(self, section_id: str) -> list[SectionVersion]:
        with self._lock:
            return list(self._versions.get(section_id, []))

    def rollback(
        self,
        section_id: str,
        target_version: int,
    ) -> str | None:
        with self._lock:
            history = self._versions.get(section_id, [])
            target = None
            for v in history:
                if v.version_number == target_version:
                    target = v
                    break
            if target is None:
                logger.warning(
                    "Rollback failed: version %d not found for section %s",
                    target_version, section_id,
                )
                return None

            logger.info(
                "Rolled back section %s to version %d",
                section_id, target_version,
            )
            return target.content

    def get_all_version_summaries(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return {
                sid: [
                    {
                        "version": v.version_number,
                        "created_at": v.created_at,
                        "content_hash": v.content_hash,
                        "reason": v.reason,
                        "validation_score": v.validation_score,
                        "tokens_used": v.tokens_used,
                    }
                    for v in versions
                ]
                for sid, versions in self._versions.items()
            }

    def clear(self) -> None:
        with self._lock:
            self._versions.clear()
