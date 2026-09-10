"""Tests for the Stage Validator."""

from __future__ import annotations

from production_pipeline.stage_validator import StageValidator


class TestStageValidator:
    def setup_method(self):
        self.validator = StageValidator()

    def test_metadata_input_valid(self):
        result = self.validator.validate_input("metadata", {})
        assert result.passed == True

    def test_transcript_input_valid(self):
        result = self.validator.validate_input("transcript", {"video_id": "test"})
        assert result.passed == True

    def test_unknown_stage_rejected(self):
        result = self.validator.validate_input("nonexistent", {})
        assert result.passed == False
        assert "Unknown stage" in result.errors[0]

    def test_missing_input_keys(self):
        result = self.validator.validate_input("analysis", {})
        assert result.passed == False

    def test_analysis_with_input(self):
        result = self.validator.validate_input("analysis", {"plain_text": "test"})
        assert result.passed == True

    def test_output_valid_always_passes(self):
        result = self.validator.validate_output("metadata", {"title": "Test"})
        assert result.passed == True

    def test_output_empty_passes(self):
        result = self.validator.validate_output("metadata", {"result": "ok"})
        assert result.passed == True

    def test_output_none_fails(self):
        result = self.validator.validate_output("metadata", None)
        assert result.passed == False

    def test_dependencies_metadata(self):
        result = self.validator.validate_dependencies("metadata", [])
        assert result.passed == True

    def test_dependencies_transcript_missing(self):
        result = self.validator.validate_dependencies("transcript", [])
        assert result.passed == False

    def test_dependencies_transcript_met(self):
        result = self.validator.validate_dependencies("transcript", ["metadata"])
        assert result.passed == True

    def test_dependencies_analysis_missing(self):
        result = self.validator.validate_dependencies("analysis", [])
        assert result.passed == False

    def test_dependencies_analysis_met(self):
        result = self.validator.validate_dependencies("analysis", ["transcript"])
        assert result.passed == True

    def test_validate_input_returns_warnings(self):
        result = self.validator.validate_input("transcript", {})
        assert hasattr(result, 'warnings')

    def test_all_inputs_have_correct_result_type(self):
        for stage in ["metadata", "transcript", "analysis"]:
            result = self.validator.validate_input(stage, {})
            assert hasattr(result, 'passed')
            assert hasattr(result, 'errors')
            assert hasattr(result, 'warnings')
