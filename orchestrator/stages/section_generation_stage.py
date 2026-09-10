"""Section Generation Stage — generates blog sections incrementally.

Consumes: outline.json, knowledge_graph.json, seo_plan.json, analysis.json
Produces: Independent section files in sections/ directory.

No existing code is modified. This stage wraps the Section Generation Engine.
"""

from __future__ import annotations

import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from section_generation.section_engine import SectionGenerationEngine
from section_generation.section_models import GenerationConfig

logger = logging.getLogger(__name__)


class SectionGenerationStage(StageExecutor):
    """Generates blog sections incrementally using the Section Generation Engine."""

    @property
    def name(self) -> str:
        return "sections"

    @property
    def dependencies(self) -> list[str]:
        return ["outline", "knowledge_graph", "seo_intelligence", "analysis"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        if not ctx.project_id:
            errors.append("project_id required for section generation stage")
        outline = ctx.get_stage_input("outline")
        if not outline:
            errors.append("outline data required for section generation")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        project_id = ctx.project_id
        outline = ctx.get_stage_input("outline")
        kg = ctx.get_stage_input("knowledge_graph")
        seo = ctx.get_stage_input("seo_intelligence") or ctx.get_stage_input("seo")
        analysis = ctx.get_stage_input("analysis")

        logger.info(
            "Section Generation Stage: generating sections for project %s",
            project_id,
        )

        engine = SectionGenerationEngine()
        engine.set_llm_provider(self._get_llm_provider(ctx))

        manifest = engine.generate_all_sections(
            project_id=project_id,
            outline=outline,
            knowledge_graph=kg,
            seo_plan=seo,
            analysis=analysis,
            config=self._build_config(ctx),
        )

        sections_list = []
        for section_id, meta in manifest.sections.items():
            content = engine.storage.load_section(
                project_id, meta.section_type, meta.order,
            ) or ""
            sections_list.append({
                "section_id": section_id,
                "type": meta.section_type.value,
                "heading": meta.heading,
                "order": meta.order,
                "content": content,
                "word_count": meta.word_count,
                "status": meta.status.value,
                "validation_score": meta.validation_score,
            })

        return StageResult(
            success=manifest.failed_sections == 0 and manifest.completed_sections > 0,
            stage=self.name,
            data={
                "sections": sections_list,
                "total_sections": manifest.total_sections,
                "completed_sections": manifest.completed_sections,
                "failed_sections": manifest.failed_sections,
                "overall_progress_pct": manifest.overall_progress_pct,
            },
            warnings=(
                [f"{manifest.failed_sections} section(s) failed"]
                if manifest.failed_sections > 0
                else []
            ),
        )

    def _build_config(self, ctx: PipelineContext) -> GenerationConfig:
        config = GenerationConfig()
        settings = ctx.settings or {}
        if isinstance(settings, dict):
            config.temperature = float(settings.get("temperature", 0.7))
            config.max_tokens = int(settings.get("max_tokens", 2048))
            config.enable_cache = bool(settings.get("enable_cache", True))
            config.enable_validation = bool(settings.get("enable_validation", True))
        return config

    def _get_llm_provider(self, ctx: PipelineContext):
        try:
            from config.settings import settings as app_settings
            from providers.llm_provider import ProviderConfig, create_provider

            key = (
                getattr(app_settings, "gemini_api_key", "")
                or getattr(app_settings, "openai_api_key", "")
                or ""
            )
            if key:
                return create_provider(ProviderConfig(
                    api_key=key,
                    model=(
                        getattr(ctx.settings, "llm_model", "gemini-2.5-flash")
                        if isinstance(ctx.settings, dict)
                        else "gemini-2.5-flash"
                    ),
                    temperature=0.7,
                    max_tokens=2048,
                ))
        except Exception:
            logger.warning("Could not create LLM provider, using mock")
            return None
