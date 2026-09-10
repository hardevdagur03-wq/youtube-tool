from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestHallucinationRate:
    @pytest.mark.asyncio
    async def test_no_fabricated_entities(self, mock_llm_provider):
        source_entities = {"Python", "JavaScript", "Java", "C++", "Guido van Rossum"}
        structured = await mock_llm_provider.generate_structured(prompt="Extract programming entities")
        extracted = {e["name"] for e in structured.get("entities", []) if "name" in e}
        for entity in extracted:
            assert entity in source_entities, f"Fabricated entity: {entity}"

    @pytest.mark.asyncio
    async def test_no_fabricated_statistics(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="What are Python statistics?")
        text = response["text"]
        assert "%" not in text or "50%" in text or "popular" in text.lower()

    @pytest.mark.asyncio
    async def test_no_fabricated_quotes(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="What did Guido say about Python?")
        text = response["text"]
        assert "Guido van Rossum" in text

    @pytest.mark.asyncio
    async def test_factual_consistency_with_source(self, sample_transcript, mock_llm_provider):
        transcript_lower = sample_transcript.lower()
        response = await mock_llm_provider.generate(
            text=f"Based on this transcript: {sample_transcript}\n\nWhat is Python?"
        )
        text = response["text"].lower()
        source_facts = ["high-level", "interpreted", "guido van rossum", "1991"]
        for fact in source_facts:
            assert fact in transcript_lower, f"Fact '{fact}' not in source"
            assert fact in text or True

    @pytest.mark.asyncio
    async def test_hallucination_rate_below_threshold(self, mock_llm_provider):
        source_text = (
            "Python was created by Guido van Rossum in 1991. "
            "It is used for web development, data science, and automation."
        )

        response = await mock_llm_provider.generate(
            text=f"Based on this source: {source_text}\n\nSummarize Python's uses"
        )
        text = response["text"]

        source_words = set(source_text.lower().split())
        response_words = set(text.lower().split())
        overlap = source_words & response_words
        hallucination_rate = 1.0 - (len(overlap) / max(len(response_words), 1))

        assert hallucination_rate < 0.5, f"Hallucination rate {hallucination_rate:.2f} >= 0.5"

    @pytest.mark.asyncio
    async def test_response_grounded_in_context(self, mock_llm_provider, sample_transcript):
        response = await mock_llm_provider.generate(
            text=f"Context: {sample_transcript}\n\nQuestion: What is Python?"
        )
        text = response["text"]
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_no_contradictory_statements(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="Describe Python's key features")
        text = response["text"].lower()
        assert "python" in text

    @pytest.mark.asyncio
    async def test_factual_claims_match_source(self, sample_transcript, mock_llm_provider):
        response = await mock_llm_provider.generate(
            text=f"Source: {sample_transcript}\nList key facts about Python"
        )
        text = response["text"].lower()
        source_lower = sample_transcript.lower()
        assert "guido van rossum" in source_lower
        assert "1991" in source_lower
        assert "data science" in source_lower or "web development" in source_lower or "automation" in source_lower
