"""Idempotency Framework — stage-level execution keys with duplicate detection.

Prevents duplicate execution of pipeline stages by enforcing idempotency
keys. Every stage execution is keyed by (execution_id + stage_name + input_hash).
If the same key already exists with "completed" status, the stage is skipped.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.exceptions import DuplicateExecutionError, IdempotencyError
from production_pipeline.models import IdempotencyKey

logger = logging.getLogger(__name__)


class IdempotencyFramework:
    """Enforces idempotent execution of pipeline stages.

    Each stage execution gets a unique key::
        key = sha256(execution_id + stage_name + input_hash)

    If the key exists with status "completed", the stage is skipped.
    If the key exists with status "running", it's a potential duplicate.
    """

    def __init__(self, config: PipelineHardeningConfig | None = None) -> None:
        self._config = config or PipelineHardeningConfig()
        self._keys: dict[str, IdempotencyKey] = {}

    def check_and_register(
        self,
        execution_id: str,
        stage_name: str,
        input_data: dict[str, Any],
    ) -> tuple[bool, IdempotencyKey | None, str | None]:
        """Check if a stage execution is a duplicate and register if new.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name.
            input_data: Stage input data (used for key derivation).

        Returns:
            Tuple of:
                is_duplicate: True if this execution has already completed.
                existing_key: The existing key if duplicate, else None.
                warning: Warning message if duplicate, else None.
        """
        input_hash = self._compute_input_hash(input_data)
        key_value = self._build_key(execution_id, stage_name, input_hash)

        existing = self._keys.get(key_value)
        if existing is not None:
            if existing.status == "completed":
                logger.warning(
                    "Duplicate execution BLOCKED: execution=%s stage=%s "
                    "key=%s (previously completed)",
                    execution_id[:8], stage_name, key_value[:16],
                )
                return True, existing, (
                    f"Stage '{stage_name}' has already completed for this "
                    f"execution with the same inputs. Skipping duplicate."
                )
            elif existing.status == "running":
                logger.warning(
                    "Duplicate execution DETECTED: execution=%s stage=%s "
                    "key=%s (currently running)",
                    execution_id[:8], stage_name, key_value[:16],
                )
                return True, existing, (
                    f"Stage '{stage_name}' is already running for this execution."
                )

        # Register new key
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self._config.idempotency_key_ttl_days
        )

        idem_key = IdempotencyKey(
            key=key_value,
            execution_id=execution_id,
            stage_name=stage_name,
            input_hash=input_hash,
            status="running",
            expires_at=expires_at.isoformat(),
        )
        self._keys[key_value] = idem_key

        logger.debug(
            "Idempotency key registered: execution=%s stage=%s key=%s",
            execution_id[:8], stage_name, key_value[:16],
        )

        return False, None, None

    def mark_completed(
        self,
        execution_id: str,
        stage_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
    ) -> None:
        """Mark an idempotency key as completed.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name.
            input_data: Stage input data.
            output_data: Stage output data.
        """
        input_hash = self._compute_input_hash(input_data)
        key_value = self._build_key(execution_id, stage_name, input_hash)
        output_hash = self._compute_input_hash(output_data)

        existing = self._keys.get(key_value)
        if existing is None:
            logger.warning(
                "No idempotency key found for completed stage: "
                "execution=%s stage=%s",
                execution_id[:8], stage_name,
            )
            return

        existing.status = "completed"
        existing.output_hash = output_hash

    def mark_failed(
        self,
        execution_id: str,
        stage_name: str,
        input_data: dict[str, Any],
    ) -> None:
        """Mark an idempotency key as failed (allows retry).

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name.
            input_data: Stage input data.
        """
        input_hash = self._compute_input_hash(input_data)
        key_value = self._build_key(execution_id, stage_name, input_hash)

        existing = self._keys.get(key_value)
        if existing:
            self._keys.pop(key_value, None)

    def check_duplicate(
        self, execution_id: str, stage_name: str, input_data: dict[str, Any]
    ) -> bool:
        """Simple duplicate check without registering.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name.
            input_data: Stage input data.

        Returns:
            True if this is a duplicate of a completed execution.
        """
        is_dup, _, _ = self.check_and_register(execution_id, stage_name, input_data)
        return is_dup

    def is_running(
        self, execution_id: str, stage_name: str, input_data: dict[str, Any]
    ) -> bool:
        """Check if a stage is currently running.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name.
            input_data: Stage input data.

        Returns:
            True if the stage is currently running.
        """
        input_hash = self._compute_input_hash(input_data)
        key_value = self._build_key(execution_id, stage_name, input_hash)
        existing = self._keys.get(key_value)
        return existing is not None and existing.status == "running"

    def get_key(
        self, execution_id: str, stage_name: str, input_data: dict[str, Any]
    ) -> IdempotencyKey | None:
        """Get the idempotency key for a stage execution.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name.
            input_data: Stage input data.

        Returns:
            ``IdempotencyKey`` if found, else None.
        """
        input_hash = self._compute_input_hash(input_data)
        key_value = self._build_key(execution_id, stage_name, input_hash)
        return self._keys.get(key_value)

    def clear(self) -> None:
        """Clear all idempotency keys."""
        self._keys.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get idempotency statistics."""
        total = len(self._keys)
        completed = sum(1 for k in self._keys.values() if k.status == "completed")
        running = sum(1 for k in self._keys.values() if k.status == "running")
        return {
            "total_keys": total,
            "completed": completed,
            "running": running,
            "duplicates_prevented": total - running,
        }

    @staticmethod
    def _build_key(execution_id: str, stage_name: str, input_hash: str) -> str:
        """Build a deterministic idempotency key."""
        raw = f"{execution_id}:{stage_name}:{input_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_input_hash(input_data: dict[str, Any]) -> str:
        """Compute a deterministic hash of input data."""
        serialized = json.dumps(input_data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
