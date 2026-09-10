"""Project Management Layer — wraps existing pipelines without modifying them.

This module adds project-level lifecycle management around the existing
Metadata, Transcript, Analysis, Blog, Review, and Export pipelines.

All existing APIs and UI continue to work unchanged.
"""

from projects.project_models import (
    Project,
    ProjectStatus,
    PipelineStage,
    StageStatus,
    PipelineStatus,
    Checkpoint,
    Version,
    HistoryEntry,
    ProjectSummary,
    ProjectSettings,
)
from projects.uuid_manager import UUIDManager
from projects.storage_manager import StorageManager
from projects.progress_tracker import ProgressTracker
from projects.checkpoint_manager import CheckpointManager
from projects.version_manager import VersionManager
from projects.history_manager import HistoryManager
from projects.recovery_engine import RecoveryEngine
from projects.project_manager import ProjectManager
from projects.project_service import ProjectService

__all__ = [
    "Project", "ProjectStatus", "PipelineStage", "StageStatus",
    "PipelineStatus", "Checkpoint", "Version", "HistoryEntry",
    "ProjectSummary", "ProjectSettings",
    "UUIDManager", "StorageManager", "ProgressTracker",
    "CheckpointManager", "VersionManager", "HistoryManager",
    "RecoveryEngine", "ProjectManager", "ProjectService",
]
