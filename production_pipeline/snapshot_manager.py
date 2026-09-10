"""Snapshot Manager — immutable stage snapshots with content integrity.

Creates content-addressed snapshots of every stage execution, including
inputs, outputs, prompt, model, provider, and generated artifacts.
Enables deterministic replay and audit verification.
Target: <500ms per snapshot save.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Any

from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.exceptions import SnapshotError, SnapshotIntegrityError
from production_pipeline.models import StageSnapshot

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages immutable stage snapshots with content integrity.

    Each snapshot is content-addressed by its SHA-256 hash.
    Snapshots are never modified after creation — they are truly immutable.
    """

    def __init__(self, config: PipelineHardeningConfig | None = None) -> None:
        self._config = config or PipelineHardeningConfig()
        self._snapshots: dict[str, list[StageSnapshot]] = {}

    def create_snapshot(
        self,
        execution_id: str,
        stage_name: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        prompt: str = "",
        model: str = "",
        provider: str = "",
        temperature: float = 0.0,
        generated_files: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        logs: list[str] | None = None,
    ) -> StageSnapshot:
        """Create an immutable snapshot of a stage execution.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Name of the stage.
            inputs: Stage input data.
            outputs: Stage output data.
            prompt: LLM prompt used (if applicable).
            model: LLM model used (if applicable).
            provider: Provider used (if applicable).
            temperature: Model temperature used.
            generated_files: List of generated file paths.
            metrics: Performance metrics.
            logs: Execution logs.

        Returns:
            ``StageSnapshot`` with content hash.
        """
        snapshot_data = {
            "inputs": inputs,
            "outputs": outputs,
            "prompt": prompt,
            "model": model,
            "provider": provider,
            "temperature": temperature,
            "generated_files": generated_files or [],
            "metrics": metrics or {},
            "logs": logs or [],
        }

        content_hash = self._compute_hash(snapshot_data)

        snapshot = StageSnapshot(
            snapshot_id=str(uuid.uuid4()),
            execution_id=execution_id,
            stage_name=stage_name,
            content_hash=content_hash,
            **snapshot_data,
        )

        if execution_id not in self._snapshots:
            self._snapshots[execution_id] = []
        self._snapshots[execution_id].append(snapshot)

        logger.info(
            "Snapshot created: execution=%s stage=%s hash=%s",
            execution_id[:8], stage_name, content_hash[:8],
        )

        return snapshot

    def get_snapshot(
        self, execution_id: str, stage_name: str
    ) -> StageSnapshot | None:
        """Get the snapshot for a specific stage.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name.

        Returns:
            ``StageSnapshot`` if found, else None.
        """
        for snap in self._snapshots.get(execution_id, []):
            if snap.stage_name == stage_name:
                return snap
        return None

    def get_snapshot_by_hash(self, content_hash: str) -> StageSnapshot | None:
        """Get a snapshot by its content hash.

        Args:
            content_hash: SHA-256 content hash.

        Returns:
            ``StageSnapshot`` if found, else None.
        """
        for snapshots in self._snapshots.values():
            for snap in snapshots:
                if snap.content_hash == content_hash:
                    return snap
        return None

    def list_snapshots(self, execution_id: str) -> list[StageSnapshot]:
        """List all snapshots for an execution.

        Args:
            execution_id: Workflow execution ID.

        Returns:
            List of ``StageSnapshot`` in order.
        """
        return list(self._snapshots.get(execution_id, []))

    def verify_integrity(
        self, execution_id: str, stage_name: str | None = None
    ) -> bool:
        """Verify snapshot content integrity by recomputing hashes.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Optional stage name filter.

        Returns:
            True if all snapshots pass integrity check.
        """
        for snap in self._snapshots.get(execution_id, []):
            if stage_name and snap.stage_name != stage_name:
                continue
            if not self._verify_single_snapshot(snap):
                return False
        return True

    def _verify_single_snapshot(self, snapshot: StageSnapshot) -> bool:
        """Verify a single snapshot's content integrity."""
        snapshot_data = {
            "inputs": snapshot.inputs,
            "outputs": snapshot.outputs,
            "prompt": snapshot.prompt,
            "model": snapshot.model,
            "provider": snapshot.provider,
            "temperature": snapshot.temperature,
            "generated_files": snapshot.generated_files,
            "metrics": snapshot.metrics,
            "logs": snapshot.logs,
        }
        recomputed = self._compute_hash(snapshot_data)
        if recomputed != snapshot.content_hash:
            logger.error(
                "Snapshot integrity FAILED: execution=%s stage=%s "
                "expected=%s actual=%s",
                snapshot.execution_id[:8], snapshot.stage_name,
                snapshot.content_hash, recomputed,
            )
            return False
        return True

    def delete_snapshots(self, execution_id: str) -> None:
        """Delete all snapshots for an execution.

        Args:
            execution_id: Workflow execution ID.
        """
        self._snapshots.pop(execution_id, None)

    def get_snapshot_chain(
        self, execution_id: str
    ) -> list[dict[str, Any]]:
        """Get a summary chain of all snapshots for an execution.

        Returns a lightweight summary without full content.

        Args:
            execution_id: Workflow execution ID.

        Returns:
            List of snapshot summaries.
        """
        return [
            {
                "snapshot_id": snap.snapshot_id,
                "stage_name": snap.stage_name,
                "content_hash": snap.content_hash[:12],
                "model": snap.model,
                "provider": snap.provider,
                "created_at": snap.created_at,
                "generated_files_count": len(snap.generated_files),
            }
            for snap in self._snapshots.get(execution_id, [])
        ]

    @staticmethod
    def _compute_hash(data: dict[str, Any]) -> str:
        """Compute a deterministic SHA-256 hash of snapshot data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
