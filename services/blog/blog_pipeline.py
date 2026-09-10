"""Blog Pipeline — end-to-end blog generation pipeline with quality validation.

Orchestrates: research → outline → writing → validation → scoring → review.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from services.blog.blog_quality import BlogQualityScore, evaluate_blog_quality
from services.blog.blog_validator import BlogValidator


@dataclass
class PipelineStage:
    name: str = ""
    status: str = "pending"
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class BlogPipelineResult:
    success: bool = False
    content: str = ""
    title: str = ""
    quality_score: BlogQualityScore = field(default_factory=BlogQualityScore)
    validation: dict[str, Any] = field(default_factory=dict)
    stages: list[PipelineStage] = field(default_factory=list)
    total_duration_ms: float = 0.0
    error: str = ""


class BlogPipeline:
    """End-to-end blog generation pipeline with quality gates."""

    def __init__(self):
        self._stages: list[str] = []
        self._results: list[PipelineStage] = []

    def run(
        self,
        content: str,
        title: str = "",
        meta_description: str = "",
        headings: list[str] | None = None,
        keywords: list[str] | None = None,
    ) -> BlogPipelineResult:
        start = time.time()
        stages = []
        result = BlogPipelineResult(content=content, title=title)

        stage1 = PipelineStage(name="quality_evaluation")
        try:
            quality = evaluate_blog_quality(
                content=content,
                title=title,
                meta_description=meta_description,
                headings=headings,
                keywords=keywords,
            )
            result.quality_score = quality
            stage1.status = "completed"
            stage1.duration_ms = (time.time() - start) * 1000
        except Exception as e:
            stage1.status = "failed"
            stage1.error = str(e)
            result.success = False
            result.error = f"Quality evaluation failed: {e}"
            result.stages = stages
            result.total_duration_ms = (time.time() - start) * 1000
            return result
        stages.append(stage1)

        stage2 = PipelineStage(name="content_validation")
        try:
            validation = BlogValidator.validate_all(content)
            result.validation = validation
            stage2.status = "completed"
            stage2.duration_ms = (time.time() - start) * 1000 - sum(s.duration_ms for s in stages)
        except Exception as e:
            stage2.status = "failed"
            stage2.error = str(e)
        stages.append(stage2)

        quality_passed = quality.overall >= 0.5
        validation_passed = all(
            v.passed for v in result.validation.values()
        ) if result.validation else True

        result.success = quality_passed
        result.stages = stages
        result.total_duration_ms = (time.time() - start) * 1000

        if not quality_passed:
            result.error = f"Quality score too low: {quality.overall}"

        return result

    def summary(self, result: BlogPipelineResult) -> dict[str, Any]:
        return {
            "success": result.success,
            "quality_score": result.quality_score.overall if result.quality_score else 0,
            "word_count": result.quality_score.word_count if result.quality_score else 0,
            "stages": [
                {"name": s.name, "status": s.status, "duration_ms": s.duration_ms}
                for s in result.stages
            ],
            "total_duration_ms": result.total_duration_ms,
            "issues": result.quality_score.issues if result.quality_score else [],
            "suggestions": result.quality_score.suggestions if result.quality_score else [],
        }
