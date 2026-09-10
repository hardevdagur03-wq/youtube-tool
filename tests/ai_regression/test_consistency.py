from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestConsistency:
    @pytest.mark.asyncio
    async def test_consistent_entity_extraction(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Extract entities from text")
        entities = structured.get("entities", [])
        assert len(entities) >= 1
        entity_names = [e["name"].lower() for e in entities]
        assert "python" in entity_names

    @pytest.mark.asyncio
    async def test_consistent_scoring(self, mock_llm_provider):
        scores = []
        for _ in range(3):
            structured = await mock_llm_provider.generate_structured(prompt="Score this content")
            scores.append(structured.get("score", 0))

        assert all(s == scores[0] for s in scores)

    @pytest.mark.asyncio
    async def test_consistent_output_structure(self, mock_llm_provider):
        results = []
        for _ in range(3):
            structured = await mock_llm_provider.generate_structured(prompt="Generate structure")
            results.append(structured)

        for r in results:
            assert set(r.keys()) == set(results[0].keys())

    @pytest.mark.asyncio
    async def test_consistent_keyword_extraction(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Extract keywords")
        keywords = structured.get("keywords", [])
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    @pytest.mark.asyncio
    async def test_consistent_section_count(self, mock_llm_provider):
        results = []
        for _ in range(3):
            structured = await mock_llm_provider.generate_structured(prompt="Generate blog sections")
            results.append(structured)

        section_counts = [len(r.get("sections", [])) for r in results]
        assert all(c == section_counts[0] for c in section_counts)

    @pytest.mark.asyncio
    async def test_consistent_output_types(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate output")
        assert isinstance(structured.get("title"), str)
        assert isinstance(structured.get("sections"), list)
        assert isinstance(structured.get("keywords"), list)
        assert isinstance(structured.get("score"), (int, float))
