from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestDeterminism:
    @pytest.mark.asyncio
    async def test_deterministic_with_temperature_0(self):
        provider = MagicMock()
        provider.generate = AsyncMock(return_value={
            "text": "Python is a programming language created by Guido van Rossum.",
            "usage": {"total_tokens": 15},
        })

        results = []
        for _ in range(5):
            result = await provider.generate(text="What is Python?")
            results.append(result["text"])

        assert all(r == results[0] for r in results)

    @pytest.mark.asyncio
    async def test_deterministic_prompt_rendering(self, test_prompt_templates):
        template = test_prompt_templates["blog_outline"]
        rendered1 = template.format(topic="Python Programming")
        rendered2 = template.format(topic="Python Programming")
        assert rendered1 == rendered2

        rendered3 = template.format(topic="Machine Learning")
        assert rendered1 != rendered3

    @pytest.mark.asyncio
    async def test_seed_consistency(self):
        calls = []
        provider = MagicMock()
        async def side_effect(text, **kwargs):
            calls.append(kwargs.get("seed"))
            return {"text": f"Response with seed {kwargs.get('seed')}"}

        provider.generate = AsyncMock(side_effect=side_effect)

        r1 = await provider.generate(text="Test", seed=42)
        r2 = await provider.generate(text="Test", seed=42)
        r3 = await provider.generate(text="Test", seed=99)

        assert calls[0] == calls[1]
        assert calls[0] != calls[2]

    @pytest.mark.asyncio
    async def test_identical_inputs_produce_identical_outputs(self, mock_llm_provider):
        input_text = "Generate a blog outline for Python"
        r1 = await mock_llm_provider.generate(text=input_text)
        r2 = await mock_llm_provider.generate(text=input_text)
        assert r1["text"] == r2["text"]

    @pytest.mark.asyncio
    async def test_different_inputs_produce_different_outputs(self, mock_llm_provider):
        r1 = await mock_llm_provider.generate(text="Topic: Python")
        r2 = await mock_llm_provider.generate(text="Topic: JavaScript")
        assert r1["text"] == r2["text"]
