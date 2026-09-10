"""Optimization Engine — main orchestrator that integrates planning, execution, revalidation, and reporting."""

from __future__ import annotations
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable

from optimization.optimization_models import (
    OptimizationConfig, OptimizationPlan, OptimizationResult,
    OptimizationReport, OptimizationStatus, OptimizedSection,
    OptimizedDraft, QualityGate, SectionType,
)
from optimization.optimization_planner import OptimizationPlanner
from optimization.optimization_executor import SectionOptimizationExecutor
from optimization.context_manager import OptimizationContextManager
from optimization.version_manager import VersionManager
from optimization.rollback_manager import RollbackManager
from optimization.retry_manager import RetryManager
from optimization.cache_manager import OptimizationCacheManager
from optimization.revalidation_engine import RevalidationEngine
from optimization.change_detector import ChangeDetector

logger = logging.getLogger(__name__)


class OptimizationEngine:
    """Main orchestrator for the Optimization Engine.

    Consumes draft.md + review_report.json + outline.json + seo_plan.json + knowledge_graph.json.
    Produces optimized_draft.md + optimization_report.json.
    """

    def __init__(
        self,
        config: OptimizationConfig | None = None,
        planner: OptimizationPlanner | None = None,
        executor: SectionOptimizationExecutor | None = None,
        context_manager: OptimizationContextManager | None = None,
        version_manager: VersionManager | None = None,
        rollback_manager: RollbackManager | None = None,
        retry_manager: RetryManager | None = None,
        cache_manager: OptimizationCacheManager | None = None,
        revalidation: RevalidationEngine | None = None,
        change_detector: ChangeDetector | None = None,
    ):
        self._config = config or OptimizationConfig()
        self._planner = planner or OptimizationPlanner(quality_gates=self._config.quality_gates)
        self._context_manager = context_manager or OptimizationContextManager()
        self._version_manager = version_manager or VersionManager(output_dir=self._config.output_dir)
        self._rollback_manager = rollback_manager or RollbackManager()
        self._retry_manager = retry_manager or RetryManager(
            max_retries=self._config.max_retries,
            quality_gates=self._config.quality_gates,
        )
        self._cache_manager = cache_manager or OptimizationCacheManager(
            cache_dir=f"{self._config.output_dir}/cache",
        )
        self._revalidation = revalidation or RevalidationEngine()
        self._change_detector = change_detector or ChangeDetector()
        self._executor = executor or SectionOptimizationExecutor(
            context_manager=self._context_manager,
            version_manager=self._version_manager,
            rollback_manager=self._rollback_manager,
            retry_manager=self._retry_manager,
            cache_manager=self._cache_manager,
            revalidation=self._revalidation,
            change_detector=self._change_detector,
            quality_gates=self._config.quality_gates,
        )

    def optimize(
        self,
        draft_md: str,
        review_report: dict,
        outline: dict,
        seo_plan: dict,
        knowledge_graph: dict,
        project: dict | None = None,
        llm_call: Callable | None = None,
        project_dir: str | None = None,
    ) -> tuple[str, OptimizationReport]:
        start = time.time()
        logger.info("[OptimizationEngine] Starting optimization")

        blog_title = review_report.get("metadata", {}).get("blog_title", "") if isinstance(review_report, dict) else ""
        project_id = review_report.get("metadata", {}).get("project_id", "") if isinstance(review_report, dict) else ""
        if project and isinstance(project, dict):
            project_id = project.get("project_id", project_id)
            blog_title = project.get("title", blog_title)

        primary_keyword = self._extract_primary_keyword(seo_plan, review_report)
        quality_scores = review_report.get("quality_scores", {}) if isinstance(review_report, dict) else {}
        issues = review_report.get("issues", []) if isinstance(review_report, dict) else []
        recommendations = review_report.get("recommendations", []) if isinstance(review_report, dict) else []

        # Parse sections from draft
        sections = self._parse_sections(draft_md)

        if not sections:
            logger.warning("[OptimizationEngine] No sections found in draft")
            return draft_md, OptimizationReport(
                project_id=project_id,
                blog_title=blog_title,
                warnings=["No sections found in draft"],
            )

        # Load artifacts for context
        artifacts = {}
        if project_dir:
            artifacts = self._context_manager.load_artifacts(project_dir)

        artifacts["outline"] = outline or artifacts.get("outline", {})
        artifacts["seo_plan"] = seo_plan or artifacts.get("seo_plan", {})
        artifacts["knowledge_graph"] = knowledge_graph or artifacts.get("knowledge_graph", {})
        artifacts["review_report"] = review_report

        # Plan optimization
        plans = self._planner.plan(
            sections=sections,
            review_scores=quality_scores,
            review_issues=issues,
            recommendations=recommendations,
            primary_keyword=primary_keyword,
        )

        plans_to_run = [p for p in plans if p.needs_optimization]
        logger.info(
            "[OptimizationEngine] Planned: %d sections need optimization out of %d total",
            len(plans_to_run), len(sections),
        )

        # Execute optimization per section
        results: list[OptimizationResult] = []
        optimized_sections: list[OptimizedSection] = []

        for i, section in enumerate(sections):
            plan = plans[i]
            section_text = section.get("content", "")
            section_heading = section.get("heading", f"Section {i+1}")
            section_type = plan.section_type

            opt_section = OptimizedSection(
                section_index=i,
                heading=section_heading,
                original_content=section_text,
                optimized_content=section_text,
                optimization_types=plan.optimization_types,
                scores_before=dict(plan.quality_scores),
                scores_after=dict(plan.quality_scores),
                status=OptimizationStatus.SKIPPED if not plan.needs_optimization else OptimizationStatus.PENDING,
            )

            if plan.needs_optimization and llm_call:
                result = self._executor.execute(
                    plan=plan,
                    section_text=section_text,
                    artifacts=artifacts,
                    llm_call=llm_call,
                    project_id=project_id,
                    blog_title=blog_title,
                )
                results.append(result)
                opt_section.optimized_content = result.content_after
                opt_section.scores_after = dict(result.scores_after)
                opt_section.status = result.status
                opt_section.optimization_types = result.optimization_types
            else:
                results.append(OptimizationResult(
                    section_index=i,
                    section_heading=section_heading,
                    section_type=section_type,
                    content_before=section_text,
                    content_after=section_text,
                    scores_before=dict(plan.quality_scores),
                    scores_after=dict(plan.quality_scores),
                    status=OptimizationStatus.SKIPPED,
                ))

            optimized_sections.append(opt_section)

        # Build optimized draft
        optimized_draft = self._build_optimized_draft(draft_md, optimized_sections)

        # Persist versions
        if project_id:
            self._version_manager.persist_versions(project_id)

        # Build report
        report = self._build_report(
            results=results,
            project_id=project_id,
            blog_title=blog_title,
            total_sections=len(sections),
            start_time=start,
            quality_scores=quality_scores,
        )

        logger.info(
            "[OptimizationEngine] Complete: %d optimized, %d skipped, %d failed in %.1fms",
            report.sections_optimized, report.sections_skipped,
            report.sections_failed, report.execution_time_ms,
        )

        return optimized_draft, report

    def _parse_sections(self, draft_md: str) -> list[dict]:
        sections: list[dict] = []
        lines = draft_md.split('\n')
        current_heading = "Preamble"
        current_content: list[str] = []
        heading_pattern = r'^(#{1,6})\s+(.+)$'

        for line in lines:
            match = __import__('re').match(heading_pattern, line)
            if match:
                if current_content:
                    sections.append({
                        "heading": current_heading,
                        "content": '\n'.join(current_content).strip(),
                    })
                current_heading = line
                current_content = [line]
            else:
                current_content.append(line)

        if current_content:
            sections.append({
                "heading": current_heading,
                "content": '\n'.join(current_content).strip(),
            })

        return sections

    def _build_optimized_draft(self, original_draft: str, optimized_sections: list[OptimizedSection]) -> str:
        import re
        lines = original_draft.split('\n')
        result_lines: list[str] = []
        section_idx = -1
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        in_section = False
        current_opt_content = ""

        for section in optimized_sections:
            if section.status == OptimizationStatus.SKIPPED or section.optimized_content == section.original_content:
                continue
            # Replace section content in draft
            if section.optimized_content:
                original = section.original_content
                optimized = section.optimized_content
                if original and original in original_draft:
                    original_draft = original_draft.replace(original, optimized, 1)

        return original_draft

    def _extract_primary_keyword(self, seo_plan: dict, review_report: dict) -> str:
        if isinstance(seo_plan, dict):
            kw_strategy = seo_plan.get("keyword_strategy", {})
            if isinstance(kw_strategy, dict):
                return kw_strategy.get("primary", "")
            return seo_plan.get("primary_keyword", "")
        if isinstance(review_report, dict):
            metadata = review_report.get("metadata", {})
            if isinstance(metadata, dict):
                return metadata.get("primary_keyword", "")
        return ""

    def _build_report(
        self,
        results: list[OptimizationResult],
        project_id: str,
        blog_title: str,
        total_sections: int,
        start_time: float,
        quality_scores: dict[str, float],
    ) -> OptimizationReport:
        optimized = [r for r in results if r.status == OptimizationStatus.SUCCESS]
        skipped = [r for r in results if r.status == OptimizationStatus.SKIPPED]
        failed = [r for r in results if r.status in (OptimizationStatus.FAILED, OptimizationStatus.MAX_RETRIES_EXCEEDED)]
        rolled_back = [r for r in results if r.rolled_back]

        # Compute overall improvement
        overall_improvement: dict[str, float] = {}
        for result in results:
            for key in result.scores_after:
                before = result.scores_before.get(key, 0)
                after = result.scores_after.get(key, 0)
                if key not in overall_improvement:
                    overall_improvement[key] = 0
                overall_improvement[key] += after - before

        n = len(results) or 1
        overall_improvement = {k: round(v / n, 1) for k, v in overall_improvement.items()}

        # Get all version history
        all_versions = []
        for result in results:
            all_versions.extend(result.retry_history)

        # Check quality gates
        final_scores = quality_scores
        if results:
            last = results[-1]
            final_scores = last.scores_after if last.scores_after else quality_scores

        quality_gates_passed = self._check_quality_gates(final_scores)

        remaining_issues = [
            {"section": r.section_heading, "type": [t.value for t in r.optimization_types],
             "status": r.status.value}
            for r in results if r.status in (OptimizationStatus.FAILED, OptimizationStatus.MAX_RETRIES_EXCEEDED, OptimizationStatus.ROLLED_BACK)
        ]

        all_warnings = []
        all_errors = []
        for r in results:
            all_warnings.extend(r.warnings)
            all_errors.extend(r.errors)

        return OptimizationReport(
            project_id=project_id,
            blog_title=blog_title,
            execution_time_ms=round((time.time() - start_time) * 1000, 1),
            total_sections=total_sections,
            sections_optimized=len(optimized),
            sections_skipped=len(skipped),
            sections_failed=len(failed),
            sections_rolled_back=len(rolled_back),
            total_retries=sum(r.retries_used for r in results),
            results=results,
            overall_improvement=overall_improvement,
            quality_gates_passed=quality_gates_passed,
            remaining_issues=remaining_issues,
            warnings=list(set(all_warnings)),
            errors=list(set(all_errors)),
            version_history=all_versions,
        )

    def _check_quality_gates(self, scores: dict[str, float]) -> bool:
        gates = self._config.quality_gates
        seo = scores.get("seo", 0)
        grammar = scores.get("grammar", 0)
        readability = scores.get("readability", 0)

        if seo < gates.seo_min:
            return False
        if grammar < gates.grammar_min:
            return False
        if readability < gates.readability_min:
            return False
        return True

    def write_outputs(
        self,
        optimized_draft: str,
        report: OptimizationReport,
        output_dir: str = "output",
        project_id: str = "",
    ) -> dict[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        paths: dict[str, str] = {}

        # Write optimized draft
        draft_filename = "optimized_draft.md"
        if project_id:
            draft_filename = f"optimized_draft_{project_id}.md"
        draft_path = os.path.join(output_dir, draft_filename)
        with open(draft_path, "w", encoding="utf-8") as f:
            f.write(optimized_draft)
        paths["optimized_draft"] = draft_path

        # Write optimization report
        report_filename = "optimization_report.json"
        if project_id:
            report_filename = f"optimization_report_{project_id}.json"
        report_path = os.path.join(output_dir, report_filename)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(json.loads(report.model_dump_json()), f, indent=2, default=str)
        paths["optimization_report"] = report_path

        logger.info("[OptimizationEngine] Outputs written: %s", paths)
        return paths
