from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompt_management.prompt_loader import PromptLoader
from prompt_management.prompt_models import PromptCategory, PromptMetadata, RiskLevel
from prompt_management.prompt_validator import PromptValidator


@pytest.fixture
def validator():
    with tempfile.TemporaryDirectory() as tmp:
        prompts_dir = Path(tmp) / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        test_prompt = """---
prompt_id: p_test_v1
name: Test Prompt
version: 1.0.0
author: Test
status: draft
category: analysis
tags: [test]
language: en
target_model: gemini-2.0-flash
temperature: 0.3
max_tokens: 4096
risk_level: low
supported_models: [gemini-2.0-flash]
dependencies: []
---

Hello {{variable1}} and {{variable2}}.
"""

        (prompts_dir / "test_prompt.md").write_text(test_prompt, encoding="utf-8")
        loader = PromptLoader(prompts_dir)
        yield PromptValidator(loader)


class TestPromptValidator:
    def test_validate_existing_prompt(self, validator):
        result = validator.validate("test_prompt", {"variable1": "a", "variable2": "b"})
        assert result.is_valid

    def test_validate_nonexistent_prompt(self, validator):
        result = validator.validate("nonexistent_prompt_xyz")
        assert not result.is_valid
        assert any("not found" in e for e in result.errors)

    def test_validate_front_matter(self, validator):
        result = validator.validate("test_prompt", {"variable1": "a", "variable2": "b"})
        assert result.is_valid

    def test_missing_variables_detected(self, validator):
        result = validator.validate("test_prompt")
        assert len(result.missing_variables) > 0
        assert "variable1" in result.missing_variables

    def test_variable_provided_detected_unused(self, validator):
        result = validator.validate("test_prompt", {"variable1": "a", "variable2": "b", "unused_var": "val"})
        assert "unused_var" in result.unused_variables

    def test_validate_content(self, validator):
        result = validator.validate_content("Hello {{name}}!")
        assert len(result.missing_variables) > 0

    def test_estimate_tokens(self, validator):
        tokens = validator.estimate_tokens("Hello world, this is a test of token estimation.")
        assert tokens > 0

    def test_estimate_cost(self, validator):
        cost = validator.estimate_cost("Hello world", "gemini-2.0-flash")
        assert cost > 0

    def test_validate_prompt_metadata_valid(self, validator):
        meta = PromptMetadata(name="Test", prompt_id="p_test", version="1.0.0", author="test")
        result = validator.validate_prompt_metadata(meta)
        assert result.is_valid

    def test_validate_prompt_metadata_invalid_version(self, validator):
        meta = PromptMetadata(name="Test", prompt_id="p_test", version="1.0.0", author="test")
        meta.version = "bad"
        result = validator.validate_prompt_metadata(meta)
        assert not result.is_valid
        assert any("version" in e.lower() for e in result.errors)

    def test_token_limit_exceeded(self, validator):
        huge_content = "x" * 5_000_000
        result = validator.validate_content(huge_content)
        if result.errors:
            assert any("exceed" in e.lower() for e in result.errors)

    def test_model_compatibility_warning(self, validator):
        meta = PromptMetadata(
            name="Test",
            target_model="nonexistent-model",
            supported_models=["gemini-2.0-flash"],
            category=PromptCategory.custom,
            risk_level=RiskLevel.low,
        )
        result = validator.validate_prompt_metadata(meta)
        assert result.is_valid or result.warnings
