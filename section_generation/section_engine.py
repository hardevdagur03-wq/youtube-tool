"""Section Generation Engine — orchestrates incremental section generation.

Manages:
- Outline consumption
- Per-section generation with independent prompts
- Checkpoint creation after every completed section
- Progress tracking (current, completed, remaining)
- Resume from last checkpoint on interruption
- Structured logging for every section
- Metrics collection
- Error handling and recovery
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from section_generation.section_models import (
    SectionType,
    SectionStatus,
    SectionOutput,
    SectionManifest,
    SectionValidation,
    SectionMetadata,
    GenerationConfig,
    ProgressReport,
    utc_now,
)
from section_generation.section_service import SectionService
from section_generation.section_storage import SectionStorage
from section_generation.section_cache import SectionCache
from section_generation.section_metadata import SectionMetadataGenerator

logger = logging.getLogger(__name__)


class SectionGenerationEngine:
    """Orchestrates incremental section generation with checkpoint support.

    The engine:
    1. Reads outline.json to determine section plan
    2. Generates each section independently
    3. Creates a checkpoint after each completed section
    4. Tracks progress (current, completed, remaining)
    5. Supports resume from last checkpoint on interruption
    6. Never regenerates completed work
    """

    def __init__(
        self,
        section_service: SectionService | None = None,
        storage: SectionStorage | None = None,
        metadata_generator: SectionMetadataGenerator | None = None,
    ) -> None:
        self._storage = storage or SectionStorage()
        if section_service:
            self._service = section_service
        else:
            self._service = SectionService(storage=self._storage)
        self._metadata_gen = metadata_generator or SectionMetadataGenerator()

        self._manifest: SectionManifest | None = None
        self._config: GenerationConfig = GenerationConfig()
        self._start_time: float = 0.0
        self._on_section_complete: Callable | None = None
        self._on_progress: Callable | None = None

    def set_llm_provider(self, provider: Any) -> None:
        self._service.set_llm_provider(provider)

    def load_artifacts(
        self,
        outline: dict[str, Any] | None = None,
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        project: dict[str, Any] | None = None,
    ) -> None:
        self._service.load_artifacts(
            outline=outline,
            knowledge_graph=knowledge_graph,
            seo_plan=seo_plan,
            analysis=analysis,
            project=project,
        )

    def set_on_section_complete(self, callback: Callable) -> None:
        self._on_section_complete = callback

    def set_on_progress(self, callback: Callable) -> None:
        self._on_progress = callback

    def generate_all_sections(
        self,
        project_id: str,
        outline: dict[str, Any] | None = None,
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        project: dict[str, Any] | None = None,
        config: GenerationConfig | None = None,
    ) -> SectionManifest:
        self.load_artifacts(outline, knowledge_graph, seo_plan, analysis, project)
        self._config = config or GenerationConfig()
        self._start_time = time.time()

        self._manifest = self._metadata_gen.create_manifest(project_id)

        sections_plan = self._get_sections_plan(outline or {})
        self._manifest.total_sections = len(sections_plan)
        self._storage.ensure_dirs(project_id)

        completed = self._load_completed_sections(project_id)
        self._manifest.completed_sections = len(completed)

        completed_ids = {s.section_id for s in completed.values()}

        logger.info(
            "Starting section generation for project %s: %d total, %d already completed",
            project_id, self._manifest.total_sections, self._manifest.completed_sections,
        )

        for i, section_spec in enumerate(sections_plan):
            section_id = section_spec.get("section_id", f"section_{i:02d}")
            if section_id in completed_ids:
                existing = completed[section_id]
                md = self._metadata_gen.create_metadata(existing)
                self._manifest = self._metadata_gen.update_manifest(self._manifest, md)
                self._emit_progress()
                continue

            section_type = section_spec.get("type", SectionType.BODY)
            plan = section_spec.get("plan", {})
            order = section_spec.get("order", i + 1)

            self._service.storage.log_event(
                project_id, section_id,
                f"generating_{section_type.value}",
                {"order": order, "heading": plan.get("heading", "")},
            )

            output, validation = self._generate_single_section(
                project_id, section_type, plan, order, section_id,
            )

            if output.status == SectionStatus.COMPLETED:
                self._service.save_section(project_id, output, validation)
                md = self._metadata_gen.create_metadata(output)
                if validation:
                    md = self._metadata_gen.update_validation_score(md, validation.score)
                self._manifest = self._metadata_gen.update_manifest(self._manifest, md)
                self._service.save_manifest(project_id, self._manifest)

                if self._on_section_complete:
                    self._on_section_complete(output, validation)

                logger.info(
                    "Section %s (%s) complete: %d words, %.1fs, score=%.1f",
                    section_id, section_type.value,
                    output.word_count, output.generation_time_ms / 1000,
                    validation.score if validation else 0,
                )
            else:
                md = self._metadata_gen.create_metadata(output)
                self._manifest = self._metadata_gen.update_manifest(self._manifest, md)
                self._service.save_manifest(project_id, self._manifest)
                logger.error(
                    "Section %s (%s) failed: %s",
                    section_id, section_type.value, output.errors,
                )
                if self._config.fail_fast:
                    break

            self._emit_progress()

        self._manifest.updated_at = utc_now()
        self._service.save_manifest(project_id, self._manifest)

        logger.info(
            "Section generation complete for project %s: "
            "%d/%d completed, %d failed, %.1f%% in %.1fs",
            project_id,
            self._manifest.completed_sections,
            self._manifest.total_sections,
            self._manifest.failed_sections,
            self._manifest.overall_progress_pct,
            time.time() - self._start_time,
        )

        return self._manifest

    def resume(
        self,
        project_id: str,
        config: GenerationConfig | None = None,
    ) -> SectionManifest | None:
        manifest = self._service.load_manifest(project_id)
        if manifest is None:
            logger.warning("No manifest found for project %s, cannot resume", project_id)
            return None

        if manifest.completed_sections >= manifest.total_sections:
            logger.info("Project %s already fully generated (%d/%d)", project_id, manifest.completed_sections, manifest.total_sections)
            return manifest

        self._manifest = manifest
        self._config = config or GenerationConfig()
        self._start_time = time.time()

        project_data = self._get_project_data(project_id)
        if project_data:
            outline = project_data.get("outline", {})
            if outline:
                self._service.load_artifacts(
                    outline=outline,
                    knowledge_graph=project_data.get("knowledge_graph"),
                    seo_plan=project_data.get("seo_plan") or project_data.get("seo_intelligence"),
                    analysis=project_data.get("analysis"),
                    project=project_data.get("project"),
                )

        sections_plan = self._get_sections_plan({})
        completed_ids = set(manifest.sections.keys())

        logger.info(
            "Resuming section generation for project %s: %d/%d completed",
            project_id, manifest.completed_sections, manifest.total_sections,
        )

        for i, section_spec in enumerate(sections_plan):
            section_id = section_spec.get("section_id", f"section_{i:02d}")
            if section_id in completed_ids:
                existing_meta = manifest.sections.get(section_id)
                if existing_meta and existing_meta.status in (
                    SectionStatus.COMPLETED, SectionStatus.CACHED,
                ):
                    continue

            section_type = section_spec.get("type", SectionType.BODY)
            plan = section_spec.get("plan", {})
            order = section_spec.get("order", i + 1)

            output, validation = self._generate_single_section(
                project_id, section_type, plan, order, section_id,
            )

            if output.status == SectionStatus.COMPLETED:
                self._service.save_section(project_id, output, validation)
                md = self._metadata_gen.create_metadata(output)
                if validation:
                    md = self._metadata_gen.update_validation_score(md, validation.score)
                self._manifest = self._metadata_gen.update_manifest(self._manifest, md)
                self._service.save_manifest(project_id, self._manifest)
            else:
                if self._config.fail_fast:
                    break

        self._manifest.updated_at = utc_now()
        self._service.save_manifest(project_id, self._manifest)
        return self._manifest

    def generate_single_section(
        self,
        project_id: str,
        section_type: SectionType,
        section_plan: dict[str, Any] | None = None,
        order: int = 0,
        config: GenerationConfig | None = None,
    ) -> tuple[SectionOutput, SectionValidation | None]:
        output, validation = self._service.generate_section(
            section_type, section_plan, order, config or self._config,
        )
        if output.status == SectionStatus.COMPLETED:
            self._service.save_section(project_id, output, validation)
            if self._manifest:
                md = self._metadata_gen.create_metadata(output)
                if validation:
                    md = self._metadata_gen.update_validation_score(md, validation.score)
                self._manifest = self._metadata_gen.update_manifest(self._manifest, md)
                self._service.save_manifest(project_id, self._manifest)
        return output, validation

    def _generate_single_section(
        self,
        project_id: str,
        section_type: SectionType,
        plan: dict[str, Any],
        order: int,
        section_id: str,
    ) -> tuple[SectionOutput, SectionValidation | None]:
        output, validation = self._service.generate_section(
            section_type, plan, order, self._config,
        )
        return output, validation

    def _get_sections_plan(self, outline: dict[str, Any]) -> list[dict[str, Any]]:
        sections_plan: list[dict[str, Any]] = []

        sections_plan.append({
            "section_id": "intro",
            "type": SectionType.INTRODUCTION,
            "plan": outline.get("intro_plan", {}),
            "order": 0,
        })

        raw_sections = outline.get("sections", [])
        if isinstance(raw_sections, list):
            for i, section in enumerate(raw_sections):
                plan = section if isinstance(section, dict) else {"heading": str(section)}
                sections_plan.append({
                    "section_id": f"section_{i + 1:02d}",
                    "type": self._detect_section_type(plan),
                    "plan": plan,
                    "order": i + 1,
                })

        faqs = outline.get("faqs", [])
        if isinstance(faqs, list) and faqs:
            sections_plan.append({
                "section_id": "faq",
                "type": SectionType.FAQ,
                "plan": faqs[0] if isinstance(faqs[0], dict) else {},
                "order": 999,
            })

        sections_plan.append({
            "section_id": "conclusion",
            "type": SectionType.CONCLUSION,
            "plan": outline.get("summary_plan", {}),
            "order": 999,
        })

        ctas = outline.get("ctas", [])
        if isinstance(ctas, list) and ctas:
            sections_plan.append({
                "section_id": "cta",
                "type": SectionType.CTA,
                "plan": ctas[0] if isinstance(ctas[0], dict) else {},
                "order": 999,
            })

        return sections_plan

    def _detect_section_type(
        self,
        plan: dict[str, Any],
    ) -> SectionType:
        goal = (plan.get("goal", "") or "").lower()
        heading = (plan.get("heading", "") or "").lower()

        type_map = {
            "problem": SectionType.PROBLEM,
            "step": SectionType.STEP_BY_STEP,
            "guide": SectionType.STEP_BY_STEP,
            "tutorial": SectionType.STEP_BY_STEP,
            "how to": SectionType.STEP_BY_STEP,
            "compare": SectionType.COMPARISON,
            "vs": SectionType.COMPARISON,
            "versus": SectionType.COMPARISON,
            "definition": SectionType.DEFINITION,
            "what is": SectionType.DEFINITION,
            "benefit": SectionType.BENEFITS,
            "advantage": SectionType.BENEFITS,
            "drawback": SectionType.DRAWBACKS,
            "disadvantage": SectionType.DRAWBACKS,
            "use case": SectionType.USE_CASES,
            "example": SectionType.EXAMPLES,
            "table": SectionType.TABLE,
            "list": SectionType.LIST,
            "code": SectionType.CODE,
            "summary": SectionType.SUMMARY,
            "recap": SectionType.SUMMARY,
        }

        for key, stype in type_map.items():
            if key in goal or key in heading:
                return stype

        return SectionType.BODY

    def _load_completed_sections(
        self,
        project_id: str,
    ) -> dict[str, SectionOutput]:
        completed: dict[str, SectionOutput] = {}
        if not self._manifest:
            return completed

        for section_id, meta in self._manifest.sections.items():
            if meta.status in (SectionStatus.COMPLETED, SectionStatus.CACHED):
                content = self._storage.load_section(
                    project_id, meta.section_type, meta.order,
                )
                if content:
                    completed[section_id] = SectionOutput(
                        section_id=section_id,
                        section_type=meta.section_type,
                        heading=meta.heading,
                        content=content,
                        order=meta.order,
                        word_count=meta.word_count,
                        version=meta.version,
                        status=SectionStatus.COMPLETED,
                    )
        return completed

    def _emit_progress(self) -> None:
        if self._on_progress and self._manifest:
            report = self._service.get_progress_report(
                self._manifest, self._start_time,
            )
            self._on_progress(report)

    def get_progress(self) -> ProgressReport | None:
        if not self._manifest:
            return None
        return self._service.get_progress_report(
            self._manifest, self._start_time,
        )

    def get_manifest(self) -> SectionManifest | None:
        return self._manifest

    def _get_project_data(self, project_id: str) -> dict[str, Any]:
        data = {}
        base = self._storage.base_path / "projects" / project_id
        if not base.exists():
            return data
        files = {
            "outline": "outline.json",
            "knowledge_graph": "knowledge_graph.json",
            "seo_plan": "seo_plan.json",
            "seo_intelligence": "seo_intelligence.json",
            "analysis": "analysis.json",
            "project": "project.json",
        }
        for key, filename in files.items():
            path = base / filename
            if path.exists():
                try:
                    import json
                    data[key] = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return data

    @property
    def cache(self) -> SectionCache:
        return self._service.cache

    @property
    def service(self) -> SectionService:
        return self._service

    @property
    def storage(self) -> SectionStorage:
        return self._storage
