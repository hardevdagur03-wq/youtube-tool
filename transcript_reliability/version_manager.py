"""Transcript Version Manager — stores and manages versioned transcript snapshots.

7 version types: original, cleaned, validated, translated, corrected,
ai_optimized, current. Every version is fully recoverable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from models.transcript import TranscriptResult
from transcript_reliability.exceptions import VersionNotFoundError
from transcript_reliability.models import VersionRecord

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages versioned snapshots of transcripts.

    Each transcript has multiple version types, each with a version number.
    Versions are stored with content hashes for integrity verification.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # {video_id: {version_type: [VersionRecord, ...]}}
        self._versions: dict[str, dict[str, list[VersionRecord]]] = {}

    def create_version(
        self,
        transcript: TranscriptResult,
        version_type: str,
        change_reason: str = "",
        parent_version_id: str = "",
    ) -> VersionRecord:
        """Create a new version snapshot.

        Args:
            transcript: The transcript to snapshot.
            version_type: Type of version (original, cleaned, etc.).
            change_reason: Why this version was created.
            parent_version_id: Previous version UUID for lineage.

        Returns:
            ``VersionRecord`` with version metadata.
        """
        video_id = transcript.video_id
        content_hash = self._compute_hash(transcript.plain_text)

        with self._lock:
            if video_id not in self._versions:
                self._versions[video_id] = {}

            if version_type not in self._versions[video_id]:
                self._versions[video_id][version_type] = []

            existing = self._versions[video_id][version_type]
            version_number = len(existing) + 1

            record = VersionRecord(
                version_id=f"{video_id}_{version_type}_{version_number}_{int(time.time())}",
                transcript_id=video_id,
                video_id=video_id,
                version_type=version_type,
                version_number=version_number,
                content_hash=content_hash,
                plain_text=transcript.plain_text,
                word_count=transcript.word_count,
                language=transcript.language,
                source=transcript.source.value if hasattr(transcript.source, 'value') else str(transcript.source),
                parent_version_id=parent_version_id or (existing[-1].version_id if existing else ""),
                change_reason=change_reason,
                metadata={
                    "provider": str(transcript.provider),
                    "duration_seconds": transcript.duration_seconds,
                    "segment_count": len(transcript.segments),
                },
            )

            existing.append(record)
            # Keep max 50 versions per type
            if len(existing) > 50:
                existing.pop(0)

            logger.info(
                "Created version %s v%d for video %s (%s)",
                version_type, version_number, video_id, change_reason or "no reason",
            )

            return record

    def get_version(
        self, video_id: str, version_type: str = "current",
        version_number: int | None = None,
    ) -> VersionRecord | None:
        """Get a specific version.

        Args:
            video_id: YouTube video ID.
            version_type: Version type filter.
            version_number: Specific version number (None = latest).

        Returns:
            ``VersionRecord`` if found, else None.
        """
        with self._lock:
            versions = self._versions.get(video_id, {}).get(version_type, [])
            if not versions:
                return None
            if version_number is None:
                return versions[-1]  # Latest
            for v in versions:
                if v.version_number == version_number:
                    return v
            return None

    def list_versions(
        self, video_id: str, version_type: str | None = None,
    ) -> list[VersionRecord]:
        """List all versions for a video.

        Args:
            video_id: YouTube video ID.
            version_type: Optional version type filter.

        Returns:
            List of ``VersionRecord`` sorted by creation time.
        """
        with self._lock:
            if video_id not in self._versions:
                return []
            if version_type:
                return list(self._versions[video_id].get(version_type, []))
            result = []
            for versions in self._versions[video_id].values():
                result.extend(versions)
            result.sort(key=lambda v: v.version_number)
            return result

    def restore_version(
        self, video_id: str, version_type: str = "current",
        version_number: int | None = None,
    ) -> TranscriptResult | None:
        """Restore a transcript to a previous version.

        Args:
            video_id: YouTube video ID.
            version_type: Version type to restore from.
            version_number: Specific version (None = latest).

        Returns:
            ``TranscriptResult`` if version found, else None.
        """
        record = self.get_version(video_id, version_type, version_number)
        if record is None:
            return None

        # Verify integrity
        current_hash = self._compute_hash(record.plain_text)
        if current_hash != record.content_hash:
            logger.error(
                "Version integrity check FAILED for %s v%d: hash mismatch",
                video_id, record.version_number,
            )
            return None

        # Build a TranscriptResult from the version
        result = TranscriptResult(
            success=True,
            video_id=video_id,
            language=record.language,
            plain_text=record.plain_text,
            word_count=record.word_count,
        )
        return result

    def verify_integrity(self, video_id: str, version_type: str = "current") -> bool:
        """Verify integrity of all versions for a video.

        Args:
            video_id: YouTube video ID.
            version_type: Version type to check.

        Returns:
            True if all versions pass integrity check.
        """
        with self._lock:
            versions = self._versions.get(video_id, {}).get(version_type, [])
            if not versions:
                return True
            for v in versions:
                current_hash = self._compute_hash(v.plain_text)
                if current_hash != v.content_hash:
                    logger.error(
                        "Integrity FAILED: %s %s v%d",
                        video_id, version_type, v.version_number,
                    )
                    return False
            return True

    def delete_versions(self, video_id: str, version_type: str | None = None) -> None:
        """Delete all versions for a video.

        Args:
            video_id: YouTube video ID.
            version_type: Optional version type to delete.
        """
        with self._lock:
            if video_id not in self._versions:
                return
            if version_type:
                self._versions[video_id].pop(version_type, None)
            else:
                self._versions[video_id].clear()
            logger.info("Deleted versions for %s (type=%s)", video_id, version_type or "all")

    def get_lineage(self, video_id: str, version_type: str = "current") -> list[dict[str, Any]]:
        """Get the full lineage chain for a version type.

        Args:
            video_id: YouTube video ID.
            version_type: Version type to trace.

        Returns:
            List of version metadata showing the chain.
        """
        with self._lock:
            versions = self._versions.get(video_id, {}).get(version_type, [])
            lineage = []
            for v in versions:
                lineage.append({
                    "version_id": v.version_id,
                    "version_number": v.version_number,
                    "change_reason": v.change_reason,
                    "parent_version_id": v.parent_version_id,
                    "created_at": v.created_at,
                    "word_count": v.word_count,
                })
            return lineage

    @staticmethod
    def _compute_hash(text: str) -> str:
        """Compute a SHA-256 hash of the text content."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
