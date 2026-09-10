from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from typing import Any


class MockLLMProvider:
    def __init__(self, responses: dict[str, str] | None = None, delay: float = 0.0):
        self._responses: dict[str, str] = responses or {}
        self._delay = delay
        self._call_history: list[dict[str, Any]] = []
        self._fail_mode: str | None = None
        self._fail_rate: float = 0.0
        self._timeout_delay: float = 0.0
        self._seed: int = 42

    def _make_key(self, prompt: str, **kwargs: Any) -> str:
        data = json.dumps({"prompt": prompt, **kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self._call_history.append({"prompt": prompt, "kwargs": kwargs, "method": "generate"})

        if self._fail_mode == "timeout":
            time.sleep(self._timeout_delay)
            raise TimeoutError(f"Simulated timeout after {self._timeout_delay}s")

        if self._fail_mode == "token_limit":
            raise ValueError("Token limit exceeded: maximum context length is 128000 tokens")

        if self._fail_mode == "rate" and random.random() < self._fail_rate:
            raise RuntimeError("Simulated LLM provider failure")

        if self._delay > 0:
            time.sleep(self._delay)

        key = self._make_key(prompt, **kwargs)
        if key in self._responses:
            return self._responses[key]

        raise KeyError(f"No canned response for prompt hash {key}")

    async def generate_async(self, prompt: str, **kwargs: Any) -> str:
        self._call_history.append({"prompt": prompt, "kwargs": kwargs, "method": "generate_async"})

        if self._fail_mode == "timeout":
            await asyncio.sleep(self._timeout_delay)
            raise TimeoutError(f"Simulated timeout after {self._timeout_delay}s")

        if self._fail_mode == "token_limit":
            raise ValueError("Token limit exceeded: maximum context length is 128000 tokens")

        if self._fail_mode == "rate" and random.random() < self._fail_rate:
            raise RuntimeError("Simulated async LLM provider failure")

        if self._delay > 0:
            await asyncio.sleep(self._delay)

        key = self._make_key(prompt, **kwargs)
        if key in self._responses:
            return self._responses[key]

        raise KeyError(f"No canned response for prompt hash {key}")

    def set_response(self, prompt: str, response: str) -> None:
        key = self._make_key(prompt)
        self._responses[key] = response

    def set_batch_responses(self, responses_dict: dict[str, str]) -> None:
        for prompt, response in responses_dict.items():
            self.set_response(prompt, response)

    def record_calls(self) -> list[dict[str, Any]]:
        return list(self._call_history)

    def clear_history(self) -> None:
        self._call_history.clear()

    def simulate_failure(self, rate: float = 0.1) -> None:
        self._fail_mode = "rate"
        self._fail_rate = max(0.0, min(1.0, rate))

    def simulate_timeout(self, delay: float = 30.0) -> None:
        self._fail_mode = "timeout"
        self._timeout_delay = delay

    def simulate_token_limit(self) -> None:
        self._fail_mode = "token_limit"

    def reset(self) -> None:
        self._responses.clear()
        self._call_history.clear()
        self._fail_mode = None
        self._fail_rate = 0.0
        self._timeout_delay = 0.0
        self._delay = 0.0
