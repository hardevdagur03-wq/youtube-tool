"""Optimization Service — high-level service layer for pipeline integration."""

from __future__ import annotations
import json
import logging
import os
from typing import Any, Callable

from optimization.optimization_engine import OptimizationEngine
from optimization.optimization_models import (
    OptimizationConfig, OptimizationReport, QualityGate,
)

logger = logging.getLogger(__name__)


class OptimizationService:
    """High-level service that integrates the Optimization Engine with the pipeline."""

    def __init__(self, config: OptimizationConfig | None = None):
        self._config = config or OptimizationConfig()
        self._engine = OptimizationEngine(config=self._config)

    def optimize_from_project(
        self,
        project_dir: str,
        llm_call: Callable | None = None,
    ) -> tuple[str | None, OptimizationReport | None]:
        project_dir = project_dir.rstrip('/\\')

        # Load artifacts
        draft_path = os.path.join(project_dir, "draft", "draft.md")
        if not os.path.exists(draft_path):
            draft_path = os.path.join(project_dir, "draft.md")

        draft_md = ""
        if os.path.exists(draft_path):
            with open(draft_path, "r", encoding="utf-8") as f:
                draft_md = f.read()

        if not draft_md:
            logger.warning("[OptimizationService] No draft found at %s", project_dir)
            return None, None

        def _load_json(filename: str) -> dict:
            path = os.path.join(project_dir, filename)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as exc:
                    logger.warning("[OptimizationService] Failed loading %s: %s", path, exc)
            return {}

        review_report = _load_json("review_report.json")
        outline = _load_json("outline.json")
        seo_plan = _load_json("seo_plan.json")
        knowledge_graph = _load_json("knowledge_graph.json")
        project_data = _load_json("project.json")

        project_id = project_data.get("project_id", "")
        output_dir = os.path.join(project_dir, self._config.output_dir.lstrip("./\\"))

        optimized_draft, report = self._engine.optimize(
            draft_md=draft_md,
            review_report=review_report,
            outline=outline,
            seo_plan=seo_plan,
            knowledge_graph=knowledge_graph,
            project=project_data,
            llm_call=llm_call,
            project_dir=project_dir,
        )

        if optimized_draft and report:
            paths = self._engine.write_outputs(
                optimized_draft=optimized_draft,
                report=report,
                output_dir=output_dir,
                project_id=project_id,
            )
            logger.info("[OptimizationService] Optimization complete for %s", project_id)
            return optimized_draft, report

        return None, report

    def optimize_from_artifacts(
        self,
        draft_md: str,
        review_report: dict,
        outline: dict,
        seo_plan: dict,
        knowledge_graph: dict,
        project: dict | None = None,
        llm_call: Callable | None = None,
    ) -> tuple[str, OptimizationReport]:
        return self._engine.optimize(
            draft_md=draft_md,
            review_report=review_report,
            outline=outline,
            seo_plan=seo_plan,
            knowledge_graph=knowledge_graph,
            project=project,
            llm_call=llm_call,
        )
