from __future__ import annotations

import pytest


pytestmark = pytest.mark.prompt


TOKEN_LIMITS = {
    "gemini": 8192,
    "gpt-4": 8192,
    "gpt-3.5": 4096,
    "claude": 8192,
    "local": 2048,
}


def estimate_tokens(text: str) -> int:
    return len(text.split())


class TestTokenCount:
    def test_token_count_accuracy(self):
        text = "Hello world, this is a test prompt with several words."
        estimated = estimate_tokens(text)
        assert estimated > 0
        assert estimated == len(text.split())

    @pytest.mark.parametrize("model,limit", TOKEN_LIMITS.items())
    def test_token_count_within_limit(self, model, limit):
        text = "word " * (limit // 2)
        tokens = estimate_tokens(text)
        assert tokens <= limit, (
            f"Prompt tokens ({tokens}) exceed limit ({limit}) for {model}"
        )

    @pytest.mark.parametrize("model,limit", TOKEN_LIMITS.items())
    def test_token_count_for_different_models(self, model, limit):
        prompt = "Analyze this YouTube video and create a blog post outline."
        tokens = estimate_tokens(prompt)
        assert tokens <= limit, (
            f"Prompt too long ({tokens} tokens) for {model} (limit {limit})"
        )
        assert tokens > 0

    def test_token_count_overflow_detection(self):
        limit = 100
        oversized_prompt = "word " * 200
        tokens = estimate_tokens(oversized_prompt)
        assert tokens > limit
        overflow = tokens - limit
        assert overflow > 0
