"""Optimization Engine — autonomous content optimization layer.

Targeted section-level optimization with revalidation, retry, rollback, and versioning.
"""

from optimization.optimization_models import (
    OptimizationType, OptimizationStatus, SectionType, QualityGate,
    OptimizationContext, OptimizationPrompt, SectionVersion,
    OptimizationResult, OptimizationPlan, OptimizationReport,
    OptimizationConfig, OptimizedSection, OptimizedDraft,
)
from optimization.optimization_engine import OptimizationEngine
from optimization.optimization_service import OptimizationService

__all__ = [
    "OptimizationType", "OptimizationStatus", "SectionType", "QualityGate",
    "OptimizationContext", "OptimizationPrompt", "SectionVersion",
    "OptimizationResult", "OptimizationPlan", "OptimizationReport",
    "OptimizationConfig", "OptimizedSection", "OptimizedDraft",
    "OptimizationEngine", "OptimizationService",
]
