"""Draft Assembly Engine — enterprise-grade document assembly.

Produces versioned, validated, production-ready drafts from
independently generated sections. No content generation occurs here.
"""

from draft.draft_assembly_engine import DraftAssemblyEngine
from draft.draft_service import DraftService
from draft.draft_models import (
    DraftDocument,
    DraftMetadata,
    DraftVersion,
    MergeLogEntry,
    MergeStatus,
    DiscoveredSection,
    SectionValidationResult,
    TableOfContentsEntry,
    AssemblyConfig,
)
from draft.draft_storage import DraftStorage, DraftStorageError
from draft.document_builder import DocumentBuilder
from draft.version_manager import DraftVersionManager
from draft.document_validator import DocumentValidator

__all__ = [
    "DraftAssemblyEngine",
    "DraftService",
    "DraftDocument",
    "DraftMetadata",
    "DraftVersion",
    "MergeLogEntry",
    "MergeStatus",
    "DiscoveredSection",
    "SectionValidationResult",
    "TableOfContentsEntry",
    "AssemblyConfig",
    "DraftStorage",
    "DraftStorageError",
    "DocumentBuilder",
    "DraftVersionManager",
    "DocumentValidator",
]
