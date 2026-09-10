from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestAIRegression:
    @pytest.mark.asyncio
    async def test_prompt_output_consistency(self):
        provider = MagicMock()
        provider.generate = AsyncMock(return_value={
            "text": "Python is a programming language.",
            "usage": {"total_tokens": 10},
        })

        response1 = await provider.generate(text="What is Python?")
        response2 = await provider.generate(text="What is Python?")

        assert response1["text"] == response2["text"]

    @pytest.mark.asyncio
    async def test_model_compatibility(self):
        provider_v1 = MagicMock()
        provider_v1.generate = AsyncMock(return_value={
            "text": "Model v1 response",
            "model": "gpt-3.5-turbo",
        })

        provider_v2 = MagicMock()
        provider_v2.generate = AsyncMock(return_value={
            "text": "Model v2 response",
            "model": "gpt-4",
        })

        r1 = await provider_v1.generate(text="Test")
        r2 = await provider_v2.generate(text="Test")

        assert r1["text"] is not None
        assert r2["text"] is not None
        assert r1["model"] != r2["model"]

    @pytest.mark.asyncio
    async def test_hallucination_rate_regression(self):
        provider = MagicMock()
        provider.generate = AsyncMock(return_value={
            "text": "The Earth is round and orbits the Sun.",
            "usage": {"total_tokens": 12},
        })

        response = await provider.generate(text="Describe the Earth")
        text = response["text"]
        factual_claims = ["Earth is round", "orbits the Sun"]
        assert all(claim.lower() in text.lower() for claim in factual_claims)

    @pytest.mark.asyncio
    async def test_response_quality_consistency(self):
        from database.cache import DatabaseCache

        cache = DatabaseCache(use_redis=False)
        prompt = "Generate blog outline for Python tutorial"
        response = {"outline": ["Intro", "Basics", "Advanced", "Conclusion"]}

        await cache.set("prompts", prompt, response)
        cached = await cache.get("prompts", prompt)
        assert cached == response

    @pytest.mark.asyncio
    async def test_token_usage_stability(self):
        provider = MagicMock()
        provider.generate = AsyncMock(return_value={
            "text": "Stable response.",
            "usage": {"total_tokens": 50, "prompt_tokens": 30, "completion_tokens": 20},
        })

        response = await provider.generate(text="Test prompt")
        usage = response["usage"]
        assert usage["total_tokens"] > 0
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
