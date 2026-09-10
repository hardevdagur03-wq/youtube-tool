"""Optimization Executor — executes targeted optimization for a single section through retry/rollback cycle."""

from __future__ import annotations
import logging
import time
from typing import Any, Callable

from optimization.optimization_models import (
    OptimizationContext, OptimizationType, OptimizationStatus,
    OptimizationPlan, OptimizationResult, SectionVersion, QualityGate,
)
from optimization.seo_optimizer import SEOOptimizer
from optimization.grammar_optimizer import GrammarOptimizer
from optimization.readability_optimizer import ReadabilityOptimizer
from optimization.hallucination_corrector import HallucinationCorrector
from optimization.prompt_builder import PromptBuilder
from optimization.context_manager import OptimizationContextManager
from optimization.version_manager import VersionManager
from optimization.rollback_manager import RollbackManager
from optimization.retry_manager import RetryManager
from optimization.cache_manager import OptimizationCacheManager
from optimization.optimization_validator import OptimizationValidator
from optimization.revalidation_engine import RevalidationEngine
from optimization.change_detector import ChangeDetector

logger = logging.getLogger(__name__)


OPTIMIZER_MAP: dict[OptimizationType, type] = {
    OptimizationType.SEO: SEOOptimizer,
    OptimizationType.GRAMMAR: GrammarOptimizer,
    OptimizationType.READABILITY: ReadabilityOptimizer,
    OptimizationType.HALLUCINATION: HallucinationCorrector,
    OptimizationType.KEYWORD: SEOOptimizer,
    OptimizationType.PASSIVE_VOICE: GrammarOptimizer,
    OptimizationType.MARKDOWN: GrammarOptimizer,
    OptimizationType.DUPLICATE: GrammarOptimizer,
    OptimizationType.STRUCTURE: GrammarOptimizer,
    OptimizationType.STYLE: GrammarOptimizer,
    OptimizationType.COMPLETENESS: GrammarOptimizer,
    OptimizationType.FAQ: GrammarOptimizer,
    OptimizationType.CTA: GrammarOptimizer,
    OptimizationType.SUMMARY: GrammarOptimizer,
}


class SectionOptimizationExecutor:
    """Executes targeted optimization for a single section through retry/rollback cycles."""

    def __init__(
        self,
        context_manager: OptimizationContextManager | None = None,
        prompt_builder: PromptBuilder | None = None,
        version_manager: VersionManager | None = None,
        rollback_manager: RollbackManager | None = None,
        retry_manager: RetryManager | None = None,
        cache_manager: OptimizationCacheManager | None = None,
        validator: OptimizationValidator | None = None,
        revalidation: RevalidationEngine | None = None,
        change_detector: ChangeDetector | None = None,
        quality_gates: QualityGate | None = None,
    ):
        self._context_manager = context_manager or OptimizationContextManager()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._version_manager = version_manager or VersionManager()
        self._rollback_manager = rollback_manager or RollbackManager()
        self._retry_manager = retry_manager or RetryManager(max_retries=3, quality_gates=quality_gates)
        self._cache_manager = cache_manager or OptimizationCacheManager()
        self._validator = validator or OptimizationValidator()
        self._revalidation = revalidation or RevalidationEngine()
        self._change_detector = change_detector or ChangeDetector()

    def execute(
        self,
        plan: OptimizationPlan,
        section_text: str,
        artifacts: dict[str, Any],
        llm_call: Callable,
        project_id: str = "",
        blog_title: str = "",
    ) -> OptimizationResult:
        start = time.time()
        result = OptimizationResult(
            section_index=plan.section_index,
            section_heading=plan.section_heading,
            section_type=plan.section_type,
            content_before=section_text,
            scores_before=dict(plan.quality_scores),
            optimization_types=list(plan.optimization_types),
        )

        if not plan.needs_optimization or not plan.optimization_types:
            result.status = OptimizationStatus.SKIPPED
            result.content_after = section_text
            result.scores_after = dict(plan.quality_scores)
            result.execution_time_ms = round((time.time() - start) * 1000, 1)
            return result

        context = self._context_manager.build_context(
            section_index=plan.section_index,
            section_text=section_text,
            section_heading=plan.section_heading,
            section_type=plan.section_type,
            optimization_types=plan.optimization_types,
            artifacts=artifacts,
            project_id=project_id,
            blog_title=blog_title,
        )

        current_text = section_text
        current_scores = dict(plan.quality_scores)

        for opt_type in plan.optimization_types:
            type_success = self._execute_optimization_type(
                result=result,
                opt_type=opt_type,
                context=context,
                current_text=current_text,
                current_scores=current_scores,
                llm_call=llm_call,
                project_id=project_id,
            )

            if type_success:
                # Update current text to optimized version
                current_text = result.content_after
                current_scores = dict(result.scores_after)
                context = context.model_copy(update={
                    "section_text": current_text,
                    "quality_scores": current_scores,
                })

        result.execution_time_ms = round((time.time() - start) * 1000, 1)
        return result

    def _execute_optimization_type(
        self,
        result: OptimizationResult,
        opt_type: OptimizationType,
        context: OptimizationContext,
        current_text: str,
        current_scores: dict[str, float],
        llm_call: Callable,
        project_id: str,
    ) -> bool:
        optimizer_class = OPTIMIZER_MAP.get(opt_type)
        if not optimizer_class:
            logger.warning("[Executor] No optimizer for %s, skipping", opt_type.value)
            return False

        optimizer = optimizer_class(self._prompt_builder)
        optimized_text = current_text
        optimized_scores = dict(current_scores)

        for attempt in range(self._retry_manager._max_retries + 1):
            if attempt > 0 and not self._retry_manager.can_retry(result.section_index):
                logger.info("[Executor] Max retries reached for section %d", result.section_index)
                result.warnings.append(f"Max retries reached for {opt_type.value}")
                break

            # Check cache
            cache_key = self._cache_manager.make_key(
                f"optimize:{opt_type.value}:s{result.section_index}:a{attempt}",
                str(hash(current_text))[:32],
            )

            cached_result = self._cache_manager.get(cache_key)
            if cached_result:
                logger.debug("[Executor] Cache hit for %s section %d", opt_type.value, result.section_index)
                optimized_text = cached_result["text"]
                result.warnings.extend(cached_result.get("warnings", []))
                result.cached = True
            else:
                optimized_text, warnings = self._run_optimizer(optimizer, opt_type, context, current_text, llm_call)
                result.warnings.extend(warnings)
                self._cache_manager.set(cache_key, {"text": optimized_text, "warnings": warnings})

            # Validate
            is_valid, validation_warnings = self._validator.validate(current_text, optimized_text, context, [opt_type])
            result.warnings.extend(validation_warnings)

            if not is_valid:
                logger.warning("[Executor] Validation failed for %s section %d: %s", opt_type.value, result.section_index, validation_warnings)
                optimized_text = current_text

            # Revalidate
            optimized_scores = self._revalidation.revalidate(
                current_text, optimized_text, [opt_type], context.primary_keyword,
            )

            # Check improvement
            has_improved = self._revalidation.has_improved(current_scores, optimized_scores, [opt_type])

            # Create version
            version = self._version_manager.create_version(
                section_index=result.section_index,
                section_heading=result.section_heading,
                prompt=f"{opt_type.value} optimization attempt {attempt+1}",
                content_before=current_text,
                content_after=optimized_text,
                scores_before=current_scores,
                scores_after=optimized_scores,
                optimization_type=opt_type,
                retry_count=attempt,
            )
            result.retry_history.append(version)

            # Check quality gates
            passed_gates = self._retry_manager.record_attempt(
                result.section_index, [opt_type], optimized_scores,
            )

            if passed_gates and has_improved:
                result.content_after = optimized_text
                result.scores_after = optimized_scores
                result.status = OptimizationStatus.SUCCESS
                result.retries_used = attempt
                logger.info("[Executor] %s successful for section %d (attempt %d)", opt_type.value, result.section_index, attempt + 1)
                return True

            # Check for rollback
            should_rollback, reason = self._rollback_manager.should_rollback(
                current_scores, optimized_scores, [opt_type],
            )
            if should_rollback:
                prev_version = self._version_manager.get_latest_version(result.section_index)
                if prev_version:
                    result = self._rollback_manager.execute_rollback(result, prev_version, reason)
                    optimized_text = result.content_after
                    optimized_scores = dict(result.scores_after)
                    logger.info("[Executor] Rolled back section %d: %s", result.section_index, reason)
                    return False

            # Update for next attempt
            if attempt < self._retry_manager._max_retries:
                context = context.model_copy(update={
                    "review_findings": context.review_findings + [
                        {"description": f"Previous {opt_type.value} optimization attempt {attempt+1} did not pass quality gates"}
                    ],
                })

        # Exhausted retries
        self._retry_manager.mark_section_result(result.section_index, result)
        result.content_after = optimized_text
        result.scores_after = optimized_scores
        result.retries_used = self._retry_manager.get_attempt_count(result.section_index)
        logger.warning("[Executor] %s failed for section %d after %d attempts", opt_type.value, result.section_index, result.retries_used)
        return False

    def _run_optimizer(
        self,
        optimizer: Any,
        opt_type: OptimizationType,
        context: OptimizationContext,
        current_text: str,
        llm_call: Callable,
    ) -> tuple[str, list[str]]:
        try:
            if opt_type == OptimizationType.SEO:
                return optimizer.optimize(context, llm_call)
            elif opt_type == OptimizationType.GRAMMAR:
                return optimizer.optimize(context, llm_call)
            elif opt_type == OptimizationType.READABILITY:
                return optimizer.optimize(context, llm_call)
            elif opt_type == OptimizationType.HALLUCINATION:
                return optimizer.optimize(context, llm_call)
            elif opt_type in (OptimizationType.KEYWORD, OptimizationType.PASSIVE_VOICE):
                return optimizer.optimize(context, llm_call)
            else:
                return optimizer.optimize(context, llm_call)
        except Exception as exc:
            logger.error("[Executor] Optimizer %s failed: %s", opt_type.value, exc)
            return current_text, [f"Optimizer {opt_type.value} failed: {exc}"]
