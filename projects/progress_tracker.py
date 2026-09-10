"""Progress Tracker — computes ETA, percentages, and stage-level progress.

No existing code is modified.
"""

from __future__ import annotations

import time
from typing import Any

from projects.project_models import (
    PipelineStage,
    StageInfo,
    StageStatus,
    STAGE_ORDER,
    utc_now,
)

STAGE_WEIGHTS = {
    PipelineStage.METADATA: 5,
    PipelineStage.TRANSCRIPT: 10,
    PipelineStage.ANALYSIS: 15,
    PipelineStage.KNOWLEDGE_GRAPH: 10,
    PipelineStage.SEO: 5,
    PipelineStage.SEO_INTELLIGENCE: 5,
    PipelineStage.OUTLINE: 10,
    PipelineStage.SECTIONS: 10,
    PipelineStage.MERGE: 5,
    PipelineStage.BLOG: 10,
    PipelineStage.REVIEW: 10,
    PipelineStage.EXPORT: 5,
}

TOTAL_WEIGHT = sum(STAGE_WEIGHTS.values())


class ProgressTracker:
    """Tracks progress across pipeline stages with ETA computation."""

    @staticmethod
    def compute_overall_progress(stages: dict[str, StageInfo]) -> float:
        if not stages:
            return 0.0
        completed_weight = 0.0
        for stage_enum in STAGE_ORDER:
            key = stage_enum.value
            info = stages.get(key)
            if info is None:
                continue
            weight = STAGE_WEIGHTS.get(stage_enum, 10)
            if info.status == StageStatus.COMPLETED:
                completed_weight += weight
            elif info.status == StageStatus.RUNNING:
                completed_weight += weight * (info.progress_pct / 100.0)
            elif info.status == StageStatus.SKIPPED:
                completed_weight += weight
        return round((completed_weight / TOTAL_WEIGHT) * 100, 1)

    @staticmethod
    def estimate_eta(start_time: float, progress_pct: float) -> float:
        if progress_pct <= 0:
            return 0.0
        elapsed = time.time() - start_time
        return max(0.0, (elapsed / (progress_pct / 100.0)) - elapsed)

    @staticmethod
    def format_duration(seconds: float) -> str:
        if seconds < 1:
            return "<1s"
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"

    @staticmethod
    def compute_speed(processed: int, elapsed: float) -> str:
        if elapsed <= 0:
            return "0 items/s"
        rate = processed / elapsed
        if rate >= 1:
            return f"{rate:.1f} items/s"
        return f"{1/rate:.1f}s/item"

    @staticmethod
    def next_stage(stages: dict[str, StageInfo]) -> str:
        for stage_enum in STAGE_ORDER:
            key = stage_enum.value
            info = stages.get(key)
            if info is None or info.status == StageStatus.PENDING:
                return key
            if info.status == StageStatus.RUNNING:
                return key
            if info.status == StageStatus.FAILED:
                return key
        return ""

    @staticmethod
    def incomplete_stages(stages: dict[str, StageInfo]) -> list[str]:
        return [
            s.value for s in STAGE_ORDER
            if stages.get(s.value) is None
            or stages[s.value].status in (StageStatus.PENDING, StageStatus.FAILED)
        ]

    @staticmethod
    def completed_stages(stages: dict[str, StageInfo]) -> list[str]:
        return [
            s.value for s in STAGE_ORDER
            if stages.get(s.value) and stages[s.value].status == StageStatus.COMPLETED
        ]

    @staticmethod
    def stage_summary(stages: dict[str, StageInfo]) -> dict[str, Any]:
        return {
            "total": len(STAGE_ORDER),
            "completed": len(ProgressTracker.completed_stages(stages)),
            "running": sum(1 for s in stages.values() if s.status == StageStatus.RUNNING),
            "pending": sum(1 for s in stages.values() if s.status == StageStatus.PENDING),
            "failed": sum(1 for s in stages.values() if s.status == StageStatus.FAILED),
            "next": ProgressTracker.next_stage(stages),
        }
