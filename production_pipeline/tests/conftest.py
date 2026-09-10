"""Test fixtures for Production Pipeline Hardening tests."""

from __future__ import annotations

import pytest

from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.checkpoint_manager import CheckpointManager
from production_pipeline.snapshot_manager import SnapshotManager
from production_pipeline.idempotency import IdempotencyFramework
from production_pipeline.transaction_logger import TransactionLogger
from production_pipeline.execution_history import ExecutionHistory
from production_pipeline.error_handler import ErrorHandler
from production_pipeline.retry_framework import RetryFramework
from production_pipeline.timeout_manager import TimeoutManager
from production_pipeline.dead_letter_queue import PipelineDeadLetterQueue
from production_pipeline.recovery_manager import RecoveryManager
from production_pipeline.resume_engine import ResumeEngine
from production_pipeline.stage_validator import StageValidator


@pytest.fixture
def test_config() -> PipelineHardeningConfig:
    config = PipelineHardeningConfig()
    config.timeout_metadata = 5
    config.timeout_transcript = 10
    config.timeout_analysis = 5
    config.checkpoint_retention_days = 1
    config.snapshot_retention_count = 5
    config.idempotency_key_ttl_days = 1
    config.snapshot_enabled = True
    config.dlq_enabled = True
    return config


@pytest.fixture
def checkpoint_manager() -> CheckpointManager:
    return CheckpointManager()


@pytest.fixture
def snapshot_manager() -> SnapshotManager:
    return SnapshotManager()


@pytest.fixture
def idempotency() -> IdempotencyFramework:
    return IdempotencyFramework()


@pytest.fixture
def tx_logger() -> TransactionLogger:
    return TransactionLogger()


@pytest.fixture
def execution_history(tx_logger) -> ExecutionHistory:
    return ExecutionHistory(tx_logger)


@pytest.fixture
def error_handler() -> ErrorHandler:
    return ErrorHandler()


@pytest.fixture
def retry_framework() -> RetryFramework:
    return RetryFramework()


@pytest.fixture
def timeout_manager() -> TimeoutManager:
    return TimeoutManager()


@pytest.fixture
def dlq() -> PipelineDeadLetterQueue:
    return PipelineDeadLetterQueue()


@pytest.fixture
def recovery_manager() -> RecoveryManager:
    return RecoveryManager()


@pytest.fixture
def resume_engine(checkpoint_manager) -> ResumeEngine:
    return ResumeEngine(checkpoint_manager)


@pytest.fixture
def stage_validator() -> StageValidator:
    return StageValidator()
