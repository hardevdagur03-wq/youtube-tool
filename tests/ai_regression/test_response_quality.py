from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestResponseQuality:
    @pytest.mark.asyncio
    async def test_response_relevance(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="Tell me about Python programming")
        text = response["text"]
        assert len(text) > 0
        assert "Python" in text

    @pytest.mark.asyncio
    async def test_response_coherence(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="Explain machine learning")
        text = response["text"]
        assert len(text) > 20
        sentences = text.split(". ")
        assert len(sentences) >= 2

    @pytest.mark.asyncio
    async def test_response_completeness(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Generate blog structure")
        assert "title" in structured
        assert "sections" in structured
        assert isinstance(structured["sections"], list)
        assert len(structured["sections"]) >= 1

    @pytest.mark.asyncio
    async def test_response_accuracy(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="Who created Python?")
        text = response["text"]
        assert "Guido van Rossum" in text

    @pytest.mark.asyncio
    async def test_structured_output_has_required_fields(self, mock_llm_provider):
        structured = await mock_llm_provider.generate_structured(prompt="Analyze content")
        assert "keywords" in structured
        assert isinstance(structured["keywords"], list)
        assert len(structured["keywords"]) > 0

    @pytest.mark.asyncio
    async def test_response_contains_key_information(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="What is Python used for?")
        text = response["text"].lower()
        key_terms = ["data science", "web development", "programming"]
        assert any(term in text for term in key_terms), f"None of {key_terms} found in response"

    @pytest.mark.asyncio
    async def test_response_length_appropriate(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="Brief explanation")
        text = response["text"]
        assert len(text) >= 20, f"Response too short: {len(text)} chars"
        assert len(text) <= 5000, f"Response too long: {len(text)} chars"

    @pytest.mark.asyncio
    async def test_no_gibberish_in_response(self, mock_llm_provider):
        response = await mock_llm_provider.generate(text="Explain Python")
        text = response["text"]
        words = text.split()
        assert len(words) >= 5
        average_word_len = sum(len(w) for w in words) / len(words)
        assert 2.0 <= average_word_len <= 15.0
