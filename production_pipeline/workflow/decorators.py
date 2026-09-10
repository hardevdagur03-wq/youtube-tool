"""Durable Stage Decorator — wraps stage executors with durability features.

The @durable_stage decorator can be applied to any stage executor function
to automatically add checkpointing, idempotency, and transaction logging.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from production_pipeline.checkpoint_manager import CheckpointManager
from production_pipeline.idempotency import IdempotencyFramework
from production_pipeline.transaction_logger import TransactionLogger

logger = logging.getLogger(__name__)

T = TypeVar("T")


def durable_stage(
    stage_name: str,
    checkpoint_manager: CheckpointManager | None = None,
    idempotency: IdempotencyFramework | None = None,
    transaction_logger: TransactionLogger | None = None,
) -> Callable:
    """Decorator that adds durability to a stage executor.

    Automatically handles:
    - Idempotency check (skip if already completed)
    - Checkpoint saving after success
    - Transaction logging
    - Error logging on failure

    Usage::

        @durable_stage("metadata", cm, idf, tl)
        async def execute_metadata(context):
            return {"title": "Video Title"}

    Args:
        stage_name: Name of the stage.
        checkpoint_manager: CheckpointManager instance.
        idempotency: IdempotencyFramework instance.
        transaction_logger: TransactionLogger instance.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            execution_id = kwargs.get("execution_id", "")
            context = kwargs.get("context", {})

            # Idempotency check
            if idempotency and execution_id:
                is_dup, _, warning = idempotency.check_and_register(
                    execution_id, stage_name, context,
                )
                if is_dup:
                    logger.info(
                        "Stage '%s' skipped (duplicate): %s",
                        stage_name, warning,
                    )
                    if transaction_logger:
                        transaction_logger.log_event(
                            execution_id, "stage_skipped_duplicate",
                            stage_name=stage_name, status="skipped",
                        )
                    result = {"success": True, "skipped": True}
                    if hasattr(func, "__call__"):
                        return result  # type: ignore
                    return result

            # Transaction log: started
            if transaction_logger and execution_id:
                transaction_logger.log_event(
                    execution_id, "stage_started",
                    stage_name=stage_name, status="running",
                )

            try:
                result = await func(*args, **kwargs)

                # Save checkpoint
                if checkpoint_manager and execution_id:
                    cp_result = result if isinstance(result, dict) else {"result": str(result)}
                    # Find stage index
                    from production_pipeline.constants import STAGE_NAMES
                    stage_index = STAGE_NAMES.index(stage_name) if stage_name in STAGE_NAMES else 0
                    checkpoint_manager.save_checkpoint(
                        execution_id, stage_name, stage_index,
                        input_data=context,
                        output_data=cp_result,
                    )

                # Mark idempotency as completed
                if idempotency and execution_id:
                    cp_result = result if isinstance(result, dict) else {"result": str(result)}
                    idempotency.mark_completed(
                        execution_id, stage_name, context, cp_result,
                    )

                # Transaction log: completed
                if transaction_logger and execution_id:
                    transaction_logger.log_event(
                        execution_id, "stage_completed",
                        stage_name=stage_name, status="completed",
                    )

                return result

            except Exception as exc:
                # Mark idempotency as failed
                if idempotency and execution_id:
                    idempotency.mark_failed(execution_id, stage_name, context)

                # Transaction log: failed
                if transaction_logger and execution_id:
                    transaction_logger.log_event(
                        execution_id, "stage_failed",
                        stage_name=stage_name, status="failed",
                        error=str(exc)[:500],
                    )

                raise

        return wrapper  # type: ignore

    return decorator
