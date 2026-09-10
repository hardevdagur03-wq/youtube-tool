"""Claude provider — Phase 7."""

from __future__ import annotations
import json
import logging
import time
from typing import Any

from modules.ai.provider import LLMProvider, LLMResponse, ProviderConfig
from exceptions.analysis_errors import LLMProviderError, LLMAuthenticationError

logger = logging.getLogger(__name__)

_COST = {
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}


def _est(model: str, inp: int, out: int) -> float:
    r = _COST.get(model.lower(), {"input": 0.003, "output": 0.015})
    return round((inp / 1000) * r["input"] + (out / 1000) * r["output"], 6)


class ClaudeProvider(LLMProvider):

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config)
        if not self.config.api_key:
            raise LLMAuthenticationError("Anthropic API key required.")
        if not self.config.model:
            self.config.model = "claude-3-haiku"
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def model_name(self) -> str:
        return self.config.model

    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise LLMProviderError("pip install anthropic")
        start = time.time()
        client = Anthropic(api_key=self.config.api_key)
        kwargs: dict = dict(model=self.config.model, max_tokens=self.config.max_output_tokens, temperature=self.config.temperature, messages=[{"role": "user", "content": prompt}])
        if system_prompt:
            kwargs["system"] = system_prompt
        try:
            resp = client.messages.create(**kwargs)
        except Exception as exc:
            raise LLMProviderError(str(exc))
        elapsed = (time.time() - start) * 1000
        usage = resp.usage
        inp = usage.input_tokens if usage else 0
        out = usage.output_tokens if usage else 0
        return LLMResponse(
            text=resp.content[0].text, provider=self.provider_name,
            model=self.config.model, input_tokens=inp, output_tokens=out,
            total_tokens=inp + out, latency_ms=round(elapsed, 1),
            cost_estimate=_est(self.config.model, inp, out),
        )

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        resp = self.generate(prompt, system_prompt)
        try:
            return json.loads(resp.text)
        except json.JSONDecodeError:
            return {"raw": resp.text}
