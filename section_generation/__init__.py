"""Section Generation Engine — enterprise-grade incremental blog section generator.

Generates each blog section independently with its own prompt, cache, retry,
validation, versioning, and storage. No monolithic LLM requests.

Consumes outline.json, knowledge_graph.json, seo_plan.json, analysis.json.
Produces sections/ with intro.md, section_*.md, faq.md, conclusion.md, cta.md.
"""

from section_generation.section_models import (
    SectionType, SectionStatus, GenerationResult,
    SectionContext, SectionPrompt, SectionOutput,
    SectionMetadata, SectionVersion, SectionValidation,
    SectionManifest, GenerationConfig, ProgressReport,
)
from section_generation.context_manager import ContextManager
from section_generation.prompt_builder import PromptBuilder
from section_generation.section_cache import SectionCache
from section_generation.section_version_manager import SectionVersionManager
from section_generation.section_validator import SectionValidator
from section_generation.section_storage import SectionStorage
from section_generation.section_metadata import SectionMetadataGenerator
from section_generation.section_generator import SectionGenerator
from section_generation.section_service import SectionService
from section_generation.section_engine import SectionGenerationEngine

__all__ = [
    "SectionType", "SectionStatus", "GenerationResult",
    "SectionContext", "SectionPrompt", "SectionOutput",
    "SectionMetadata", "SectionVersion", "SectionValidation",
    "SectionManifest", "GenerationConfig", "ProgressReport",
    "ContextManager", "PromptBuilder", "SectionCache",
    "SectionVersionManager", "SectionValidator", "SectionStorage",
    "SectionMetadataGenerator", "SectionGenerator", "SectionService",
    "SectionGenerationEngine",
]
