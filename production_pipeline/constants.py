"""Constants and enums for Production Pipeline Hardening."""

from __future__ import annotations

from enum import Enum


# ===================================================================
# Workflow States
# ===================================================================


class WorkflowState(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    RETRYING = "retrying"
    RECOVERING = "recovering"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    DEAD_LETTER = "dead_letter"


# Valid state transitions: {from_state: [to_state]}
WORKFLOW_TRANSITIONS: dict[WorkflowState, list[WorkflowState]] = {
    WorkflowState.CREATED: [WorkflowState.QUEUED, WorkflowState.CANCELLED],
    WorkflowState.QUEUED: [WorkflowState.RUNNING, WorkflowState.CANCELLED],
    WorkflowState.RUNNING: [
        WorkflowState.WAITING, WorkflowState.RETRYING,
        WorkflowState.RECOVERING, WorkflowState.PAUSED,
        WorkflowState.COMPLETED, WorkflowState.FAILED,
    ],
    WorkflowState.WAITING: [WorkflowState.RUNNING, WorkflowState.CANCELLED],
    WorkflowState.RETRYING: [WorkflowState.RUNNING, WorkflowState.DEAD_LETTER, WorkflowState.FAILED],
    WorkflowState.RECOVERING: [WorkflowState.RUNNING, WorkflowState.FAILED],
    WorkflowState.PAUSED: [WorkflowState.RUNNING, WorkflowState.CANCELLED],
    WorkflowState.COMPLETED: [WorkflowState.ARCHIVED],
    WorkflowState.FAILED: [WorkflowState.RETRYING, WorkflowState.RECOVERING, WorkflowState.ARCHIVED, WorkflowState.DEAD_LETTER],
    WorkflowState.CANCELLED: [WorkflowState.ARCHIVED],
    WorkflowState.ARCHIVED: [],
    WorkflowState.DEAD_LETTER: [WorkflowState.RETRYING, WorkflowState.ARCHIVED],
}

TERMINAL_WORKFLOW_STATES = {WorkflowState.COMPLETED, WorkflowState.CANCELLED, WorkflowState.ARCHIVED}


# ===================================================================
# Stage States
# ===================================================================


class StageState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


STAGE_TRANSITIONS: dict[StageState, list[StageState]] = {
    StageState.PENDING: [StageState.READY, StageState.SKIPPED],
    StageState.READY: [StageState.RUNNING, StageState.SKIPPED],
    StageState.RUNNING: [StageState.COMPLETED, StageState.FAILED, StageState.TIMEOUT, StageState.RETRYING],
    StageState.COMPLETED: [],
    StageState.FAILED: [StageState.RETRYING, StageState.READY],
    StageState.SKIPPED: [],
    StageState.TIMEOUT: [StageState.RETRYING, StageState.READY],
    StageState.RETRYING: [StageState.RUNNING, StageState.FAILED],
}

TERMINAL_STAGE_STATES = {StageState.COMPLETED, StageState.SKIPPED}


# ===================================================================
# Error Classification
# ===================================================================


class ErrorClass(str, Enum):
    APPLICATION = "application"
    VALIDATION = "validation"
    AI = "ai"
    DATABASE = "database"
    REDIS = "redis"
    TIMEOUT = "timeout"
    NETWORK = "network"
    WORKER = "worker"
    STORAGE = "storage"
    EXTERNAL_API = "external_api"
    UNKNOWN = "unknown"


# ===================================================================
# Timeout defaults per stage
# ===================================================================

STAGE_TIMEOUT_DEFAULTS: dict[str, int] = {
    "metadata": 15,
    "transcript": 60,
    "analysis": 45,
    "knowledge_graph": 20,
    "seo": 20,
    "outline": 20,
    "sections": 60,
    "review": 20,
    "export": 20,
    "publishing": 30,
}


# ===================================================================
# Idempotency
# ===================================================================

STAGE_NAMES = [
    "metadata", "transcript", "analysis", "knowledge_graph",
    "seo", "outline", "sections", "review", "export", "publishing",
]
