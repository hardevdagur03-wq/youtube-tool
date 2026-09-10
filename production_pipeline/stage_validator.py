"""Stage Validator — validates inputs, outputs, and dependencies for every stage.

Ensures no stage continues with invalid output and no stage starts without
valid inputs.
"""

from __future__ import annotations

import logging
from typing import Any

from production_pipeline.constants import STAGE_NAMES
from production_pipeline.exceptions import ValidationError
from production_pipeline.models import ValidationResult

logger = logging.getLogger(__name__)

# Required input keys per stage
_STAGE_INPUT_REQUIREMENTS: dict[str, list[str]] = {
    "metadata": [],
    "transcript": [],
    "analysis": ["plain_text"],
    "knowledge_graph": ["transcript", "analysis"],
    "seo": ["analysis"],
    "outline": ["analysis", "seo"],
    "sections": ["outline"],
    "review": ["sections"],
    "export": ["sections"],
    "publishing": ["export"],
}

# Required output keys per stage (performed by the stage)
_STAGE_OUTPUT_REQUIREMENTS: dict[str, list[str]] = {
    "metadata": [],
    "transcript": [],
    "analysis": [],
    "knowledge_graph": [],
    "seo": [],
    "outline": [],
    "sections": [],
    "review": [],
    "export": [],
    "publishing": [],
}


class StageValidator:
    """Validates stage inputs, outputs, and dependencies.

    Every stage's inputs are validated BEFORE execution.
    Every stage's outputs are validated AFTER execution.
    Dependencies are checked to ensure upstream stages completed.
    """

    def validate_input(
        self, stage_name: str, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate stage inputs before execution.

        Args:
            stage_name: Name of the stage to validate.
            context: Pipeline context dict containing all stage outputs so far.

        Returns:
            ``ValidationResult`` with pass/fail and error details.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if stage_name not in STAGE_NAMES:
            errors.append(f"Unknown stage: {stage_name}")

        # Check required input keys exist in context
        required = _STAGE_INPUT_REQUIREMENTS.get(stage_name, [])
        for key in required:
            if key not in context or context.get(key) is None:
                errors.append(
                    f"Missing required input '{key}' for stage '{stage_name}'"
                )

        # Check dependency stages have output
        deps = self._get_dependencies(stage_name)
        for dep in deps:
            if dep not in context or not context.get(dep):
                warnings.append(
                    f"Dependency '{dep}' has no output for stage '{stage_name}'"
                )

        result = ValidationResult(
            passed=len(errors) == 0,
            stage_name=stage_name,
            errors=errors,
            warnings=warnings,
            input_valid=len(errors) == 0,
        )

        if not result.passed:
            logger.warning(
                "Input validation FAILED for stage '%s': %s",
                stage_name, errors,
            )

        return result

    def validate_output(
        self, stage_name: str, output: dict[str, Any]
    ) -> ValidationResult:
        """Validate stage outputs after execution.

        Args:
            stage_name: Name of the stage that executed.
            output: The output dict produced by the stage.

        Returns:
            ``ValidationResult`` with pass/fail and error details.
        """
        errors: list[str] = []

        if not output:
            errors.append(f"Stage '{stage_name}' produced no output")

        required = _STAGE_OUTPUT_REQUIREMENTS.get(stage_name, [])
        for key in required:
            if key not in output:
                errors.append(
                    f"Missing required output '{key}' for stage '{stage_name}'"
                )

        result = ValidationResult(
            passed=len(errors) == 0,
            stage_name=stage_name,
            errors=errors,
            output_valid=len(errors) == 0,
        )

        if not result.passed:
            logger.warning(
                "Output validation FAILED for stage '%s': %s",
                stage_name, errors,
            )

        return result

    def validate_dependencies(
        self, stage_name: str, completed_stages: list[str]
    ) -> ValidationResult:
        """Check that all dependencies for a stage are completed.

        Args:
            stage_name: Name of the stage to check.
            completed_stages: List of already completed stage names.

        Returns:
            ``ValidationResult`` with pass/fail.
        """
        errors: list[str] = []
        deps = self._get_dependencies(stage_name)

        for dep in deps:
            if dep not in completed_stages:
                errors.append(
                    f"Dependency '{dep}' not completed for stage '{stage_name}'"
                )

        result = ValidationResult(
            passed=len(errors) == 0,
            stage_name=stage_name,
            errors=errors,
            dependencies_valid=len(errors) == 0,
        )

        return result

    @staticmethod
    def _get_dependencies(stage_name: str) -> list[str]:
        """Get dependency list for a stage."""
        from orchestrator.dependency_resolver import STAGE_DEPENDENCIES
        return STAGE_DEPENDENCIES.get(stage_name, [])
