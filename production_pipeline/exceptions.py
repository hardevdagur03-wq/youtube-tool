"""Exception hierarchy for Production Pipeline Hardening."""

from __future__ import annotations


class PipelineHardeningError(Exception):
    """Base exception for all pipeline hardening errors."""
    pass


class WorkflowStateError(PipelineHardeningError):
    """Illegal workflow state transition."""
    pass


class StageStateError(PipelineHardeningError):
    """Illegal stage state transition."""
    pass


class CheckpointError(PipelineHardeningError):
    """Checkpoint operation failed."""
    pass


class CheckpointNotFoundError(PipelineHardeningError):
    """Requested checkpoint does not exist."""
    pass


class SnapshotError(PipelineHardeningError):
    """Snapshot operation failed."""
    pass


class SnapshotIntegrityError(PipelineHardeningError):
    """Snapshot content hash verification failed."""
    pass


class IdempotencyError(PipelineHardeningError):
    """Idempotency check failed."""
    pass


class DuplicateExecutionError(PipelineHardeningError):
    """Duplicate execution detected and blocked."""
    pass


class TransactionLogError(PipelineHardeningError):
    """Transaction log operation failed."""
    pass


class TimeoutError(PipelineHardeningError):
    """Stage execution timed out."""
    pass


class RecoveryError(PipelineHardeningError):
    """Recovery operation failed."""
    pass


class ResumeError(PipelineHardeningError):
    """Pipeline resume failed."""
    pass


class DeadLetterError(PipelineHardeningError):
    """Dead letter queue operation failed."""
    pass


class ValidationError(PipelineHardeningError):
    """Stage validation failed."""
    pass


class ExecutionHistoryError(PipelineHardeningError):
    """Execution history operation failed."""
    pass
