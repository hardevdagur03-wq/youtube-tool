"""Section Service — high-level integration layer for section generation.

Wires together ContextManager, PromptBuilder, SectionGenerator,
SectionValidator, SectionCache, SectionVersionManager, SectionStorage,
and SectionMetadataGenerator into a single service.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from section_generation.section_models import (
    SectionType,
    SectionStatus,
    SectionContext,
    SectionOutput,
    SectionManifest,
    SectionValidation,
    GenerationConfig,
    ProgressReport,
    generate_section_id,
    estimate_reading_time_seconds,
    utc_now,
)
from section_generation.context_manager import ContextManager
from section_generation.prompt_builder import PromptBuilder
from section_generation.section_generator import SectionGenerator
from section_generation.section_validator import SectionValidator
from section_generation.section_cache import SectionCache
from section_generation.section_version_manager import SectionVersionManager
from section_generation.section_storage import SectionStorage
from section_generation.section_metadata import SectionMetadataGenerator

logger = logging.getLogger(__name__)


class SectionService:
    """High-level service for section generation.

    Integrates with ProjectManager, PipelineOrchestrator.
    Does NOT modify any existing modules.
    """

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        prompt_builder: PromptBuilder | None = None,
        generator: SectionGenerator | None = None,
        validator: SectionValidator | None = None,
        cache: SectionCache | None = None,
        version_manager: SectionVersionManager | None = None,
        storage: SectionStorage | None = None,
        metadata_generator: SectionMetadataGenerator | None = None,
        llm_provider: Any = None,
    ) -> None:
        self._context_manager = context_manager or ContextManager()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._generator = generator or SectionGenerator(
            prompt_builder=self._prompt_builder,
            context_manager=self._context_manager,
        )
        self._validator = validator or SectionValidator()
        self._cache = cache or SectionCache()
        self._version_manager = version_manager or SectionVersionManager()
        self._storage = storage or SectionStorage()
        self._metadata_gen = metadata_generator or SectionMetadataGenerator()

        if llm_provider:
            self._generator.set_llm_provider(llm_provider)

    def set_llm_provider(self, provider: Any) -> None:
        self._generator.set_llm_provider(provider)

    def load_artifacts(
        self,
        outline: dict[str, Any] | None = None,
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        project: dict[str, Any] | None = None,
    ) -> None:
        self._context_manager.load(
            outline=outline,
            knowledge_graph=knowledge_graph,
            seo_plan=seo_plan,
            analysis=analysis,
            project=project,
        )

    def generate_section(
        self,
        section_type: SectionType,
        section_plan: dict[str, Any] | None = None,
        order: int = 0,
        config: GenerationConfig | None = None,
        validate: bool = True,
    ) -> tuple[SectionOutput, SectionValidation | None]:
        cfg = config or GenerationConfig()
        ctx = self._context_manager.get_context_for_section(
            section_type, section_plan, order,
        )
        output = self._generator.generate(section_type, ctx, cfg)

        validation = None
        if validate and output.status == SectionStatus.COMPLETED:
            validation = self._validator.validate(output, ctx)
            if not validation.valid:
                logger.warning(
                    "Section %s (%s) validation failed: score=%.1f, issues=%s",
                    output.section_id, section_type.value,
                    validation.score, validation.issues,
                )

        return output, validation

    def generate_introduction(
        self,
        config: GenerationConfig | None = None,
    ) -> tuple[SectionOutput, SectionValidation | None]:
        return self.generate_section(
            SectionType.INTRODUCTION,
            self._context_manager.get_intro_plan(),
            order=0,
            config=config,
        )

    def generate_body_section(
        self,
        section_plan: dict[str, Any],
        order: int,
        section_type: SectionType = SectionType.BODY,
        config: GenerationConfig | None = None,
    ) -> tuple[SectionOutput, SectionValidation | None]:
        section_type = self._detect_section_type(section_plan, section_type)
        return self.generate_section(
            section_type,
            section_plan,
            order=order,
            config=config,
        )

    def generate_faq(
        self,
        config: GenerationConfig | None = None,
    ) -> tuple[SectionOutput, SectionValidation | None]:
        faq_plans = self._context_manager.get_faq_plan()
        return self.generate_section(
            SectionType.FAQ,
            faq_plans[0] if faq_plans else None,
            order=999,
            config=config,
        )

    def generate_conclusion(
        self,
        config: GenerationConfig | None = None,
    ) -> tuple[SectionOutput, SectionValidation | None]:
        return self.generate_section(
            SectionType.CONCLUSION,
            self._context_manager.get_summary_plan(),
            order=999,
            config=config,
        )

    def generate_cta(
        self,
        config: GenerationConfig | None = None,
    ) -> tuple[SectionOutput, SectionValidation | None]:
        cta_plans = self._context_manager.get_cta_plan()
        return self.generate_section(
            SectionType.CTA,
            cta_plans[0] if cta_plans else None,
            order=999,
            config=config,
        )

    def save_section(
        self,
        project_id: str,
        output: SectionOutput,
        validation: SectionValidation | None = None,
    ) -> Path:
        filepath = self._storage.save_section(project_id, output)

        if validation:
            self._storage.save_validation(project_id, output.section_id, validation)

        self._storage.log_event(project_id, output.section_id, "saved", {
            "type": output.section_type.value,
            "word_count": output.word_count,
            "status": output.status.value,
        })

        sv = self._version_manager.create_version(
            output.section_id, output,
            reason=f"generated_{output.section_type.value}",
        )
        self._storage.save_version(project_id, output.section_id, sv)

        return filepath

    def save_manifest(
        self,
        project_id: str,
        manifest: SectionManifest,
    ) -> Path:
        return self._storage.save_manifest(project_id, manifest)

    def load_manifest(self, project_id: str) -> SectionManifest | None:
        return self._storage.load_manifest(project_id)

    def validate_section(
        self,
        output: SectionOutput,
        context: SectionContext | None = None,
    ) -> SectionValidation:
        if context is None:
            context = self._context_manager.get_context_for_section(
                output.section_type,
                {"heading": output.heading},
                order=output.order,
            )
        return self._validator.validate(output, context)

    def _detect_section_type(
        self,
        plan: dict[str, Any],
        default: SectionType = SectionType.BODY,
    ) -> SectionType:
        mapping = {
            "problem": SectionType.PROBLEM,
            "explanation": SectionType.EXPLANATION,
            "step_by_step": SectionType.STEP_BY_STEP,
            "comparison": SectionType.COMPARISON,
            "definition": SectionType.DEFINITION,
            "benefits": SectionType.BENEFITS,
            "drawbacks": SectionType.DRAWBACKS,
            "use_cases": SectionType.USE_CASES,
            "examples": SectionType.EXAMPLES,
            "case_study": SectionType.CASE_STUDIES,
            "table": SectionType.TABLE,
            "list": SectionType.LIST,
            "code": SectionType.CODE,
            "quote": SectionType.QUOTE,
            "body": SectionType.BODY,
        }
        goal = (plan.get("goal", "") or "").lower()
        for key, stype in mapping.items():
            if key in goal:
                return stype
        return default

    def get_progress_report(
        self,
        manifest: SectionManifest,
        start_time: float = 0.0,
    ) -> ProgressReport:
        elapsed = (time.time() - start_time) if start_time > 0 else 0.0
        avg_time = (
            elapsed / max(manifest.completed_sections, 1)
            if manifest.completed_sections > 0
            else 0.0
        )
        remaining = manifest.pending_sections + manifest.failed_sections
        eta = avg_time * remaining / 1000 if avg_time > 0 else 0.0

        return ProgressReport(
            total_sections=manifest.total_sections,
            completed=manifest.completed_sections,
            failed=manifest.failed_sections,
            pending=manifest.pending_sections,
            progress_pct=manifest.overall_progress_pct,
            elapsed_seconds=round(elapsed, 1),
            estimated_remaining_seconds=round(eta, 1),
            avg_section_time_ms=round(avg_time * 1000, 1) if avg_time > 0 else 0.0,
        )

    @property
    def storage(self) -> SectionStorage:
        return self._storage

    @property
    def version_manager(self) -> SectionVersionManager:
        return self._version_manager

    @property
    def cache(self) -> SectionCache:
        return self._cache
