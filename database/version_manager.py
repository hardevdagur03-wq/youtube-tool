from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from database.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class VersionManager:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_version(
        self,
        entity_type: str,
        entity_uuid: str,
        project_uuid: str,
        snapshot: dict[str, Any],
        changed_fields: list[str] | None = None,
        changed_by: str = "system",
        pipeline_stage: str = "",
        extra_data: dict[str, Any] | None = None,
    ) -> int:
        prev = await self.uow.version_history.get_latest_version(
            entity_type, entity_uuid
        )
        version_number = (prev.version_number + 1) if prev else 1

        safe_snapshot = self._make_json_safe(snapshot)
        checksum = self._compute_checksum(safe_snapshot)
        snapshot_json = json.dumps(safe_snapshot, sort_keys=True, default=str)

        await self.uow.version_history.create(
            project_uuid=project_uuid,
            entity_type=entity_type,
            entity_uuid=entity_uuid,
            version_number=version_number,
            previous_version_uuid=prev.uuid if prev else None,
            previous_version_number=prev.version_number if prev else 0,
            snapshot=safe_snapshot,
            changed_fields=changed_fields or [],
            changed_by=changed_by,
            pipeline_stage=pipeline_stage,
            checksum=checksum,
            extra_data=extra_data or {},
            size_bytes=len(snapshot_json.encode("utf-8")),
        )

        await self.uow.history.log_event(
            action=f"{entity_type}.version_created",
            entity_type=entity_type,
            entity_uuid=entity_uuid,
            project_uuid=project_uuid,
            actor_id=changed_by,
            extra_data={
                "version": version_number,
                "changed_fields": changed_fields,
                "pipeline_stage": pipeline_stage,
            },
        )

        logger.info(
            "Version %d created for %s %s",
            version_number, entity_type, entity_uuid[:8],
        )
        return version_number

    async def get_version(
        self, entity_type: str, entity_uuid: str, version_number: int
    ) -> dict[str, Any] | None:
        version = await self.uow.version_history.get_version(
            entity_type, entity_uuid, version_number
        )
        if version is None:
            return None
        return version.snapshot

    async def list_versions(
        self, entity_type: str, entity_uuid: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        versions = await self.uow.version_history.list_by_entity(
            entity_type, entity_uuid, limit
        )
        return [
            {
                "version": v.version_number,
                "timestamp": v.created_at.isoformat() if hasattr(v.created_at, 'isoformat') else str(v.created_at),
                "changed_by": v.changed_by,
                "pipeline_stage": v.pipeline_stage,
                "changed_fields": v.changed_fields,
                "checksum": v.checksum,
                "size_bytes": v.size_bytes,
            }
            for v in versions
        ]

    async def get_latest_version(
        self, entity_type: str, entity_uuid: str
    ) -> int:
        version = await self.uow.version_history.get_latest_version(
            entity_type, entity_uuid
        )
        return version.version_number if version else 0

    async def compare_versions(
        self,
        entity_type: str,
        entity_uuid: str,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        snap_a = await self.get_version(entity_type, entity_uuid, version_a)
        snap_b = await self.get_version(entity_type, entity_uuid, version_b)

        if snap_a is None or snap_b is None:
            raise ValueError(f"Version not found: {version_a if snap_a is None else version_b}")

        keys_a = set(snap_a.keys())
        keys_b = set(snap_b.keys())
        added = keys_b - keys_a
        removed = keys_a - keys_b
        common = keys_a & keys_b

        changed = {}
        for key in common:
            if snap_a[key] != snap_b[key]:
                changed[key] = {"from": snap_a[key], "to": snap_b[key]}

        return {
            "version_a": version_a,
            "version_b": version_b,
            "added_fields": list(added),
            "removed_fields": list(removed),
            "changed_fields": changed,
            "unchanged_count": len(common) - len(changed),
        }

    @staticmethod
    def _compute_checksum(data: dict[str, Any]) -> str:
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _make_json_safe(data: dict[str, Any]) -> dict[str, Any]:
        def convert(val: Any) -> Any:
            if isinstance(val, dict):
                return {k: convert(v) for k, v in val.items()}
            if isinstance(val, list):
                return [convert(v) for v in val]
            if hasattr(val, "isoformat"):
                return val.isoformat()
            if hasattr(val, "hex"):
                return str(val)
            return val
        return convert(data)
