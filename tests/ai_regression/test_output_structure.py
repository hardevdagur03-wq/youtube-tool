from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestOutputStructure:
    @pytest.mark.asyncio
    async def test_output_schema_adherence(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate structured output")
        expected_schema = {"title", "sections", "keywords", "entities", "score"}
        actual_keys = set(structured.keys())
        assert expected_schema.issubset(actual_keys), f"Missing keys: {expected_schema - actual_keys}"

    @pytest.mark.asyncio
    async def test_output_field_types(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate typed output")
        assert isinstance(structured["title"], str)
        assert isinstance(structured["sections"], list)
        assert isinstance(structured["keywords"], list)
        assert isinstance(structured["entities"], list)
        assert isinstance(structured["score"], (int, float))

    @pytest.mark.asyncio
    async def test_output_required_fields(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate required fields")
        required = ["title", "sections", "score"]
        for field in required:
            assert field in structured, f"Required field '{field}' missing"
            assert structured[field] is not None, f"Required field '{field}' is None"

    @pytest.mark.asyncio
    async def test_output_no_extra_fields(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate output")
        allowed_keys = {"title", "sections", "keywords", "entities", "score"}
        for key in structured:
            assert key in allowed_keys, f"Unexpected key: {key}"

    @pytest.mark.asyncio
    async def test_section_structure_valid(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate sections")
        sections = structured.get("sections", [])
        for section in sections:
            assert "heading" in section
            assert "content" in section
            assert isinstance(section["heading"], str)
            assert isinstance(section["content"], str)
            assert len(section["heading"]) > 0

    @pytest.mark.asyncio
    async def test_entity_structure_valid(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate entities")
        entities = structured.get("entities", [])
        for entity in entities:
            assert "name" in entity
            assert "type" in entity
            assert isinstance(entity["name"], str)
            assert isinstance(entity["type"], str)

    @pytest.mark.asyncio
    async def test_keyword_list_non_empty(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate keywords")
        keywords = structured.get("keywords", [])
        assert len(keywords) > 0
        for kw in keywords:
            assert isinstance(kw, str)
            assert len(kw) > 0

    @pytest.mark.asyncio
    async def test_score_within_range(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate score")
        score = structured.get("score", 0)
        assert 0 <= score <= 100, f"Score {score} out of range [0, 100]"
