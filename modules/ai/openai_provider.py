"""OpenAI provider — Phase 7."""

from __future__ import annotations
import json
import logging
import time
from typing import Any

from modules.ai.provider import LLMProvider, LLMResponse, ProviderConfig
from exceptions.analysis_errors import LLMProviderError, LLMAuthenticationError

logger = logging.getLogger(__name__)

_COST = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}


def _est(model: str, inp: int, out: int) -> float:
    r = _COST.get(model.lower(), {"input": 0.002, "output": 0.008})
    return round((inp / 1000) * r["input"] + (out / 1000) * r["output"], 6)


class OpenAIProvider(LLMProvider):

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config)
        if not self.config.api_key:
            raise LLMAuthenticationError("OpenAI API key required.")
        if not self.config.model:
            self.config.model = "gpt-4o-mini"
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.config.model

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.config.api_key)
            except ImportError:
                raise LLMProviderError("pip install openai")
        return self._client

    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        start = time.time()
        client = self._get_client()
        msgs: list[dict] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        try:
            resp = client.chat.completions.create(
                model=self.config.model, messages=msgs,
                temperature=self.config.temperature,
                max_tokens=self.config.max_output_tokens,
                timeout=self.config.timeout_secs,
            )
        except Exception as exc:
            raise LLMProviderError(str(exc))
        elapsed = (time.time() - start) * 1000
        choice = resp.choices[0]
        usage = resp.usage
        inp = usage.prompt_tokens if usage else 0
        out = usage.completion_tokens if usage else 0
        return LLMResponse(
            text=choice.message.content or "", provider=self.provider_name,
            model=self.config.model, input_tokens=inp, output_tokens=out,
            total_tokens=inp + out, latency_ms=round(elapsed, 1),
            cost_estimate=_est(self.config.model, inp, out),
        )

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        start = time.time()
        client = self._get_client()
        msgs: list[dict] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        try:
            resp = client.chat.completions.create(
                model=self.config.model, messages=msgs,
                temperature=self.config.temperature,
                max_tokens=self.config.max_output_tokens,
                timeout=self.config.timeout_secs,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LLMProviderError(str(exc))
        elapsed = (time.time() - start) * 1000
        text = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"raw": text}
        usage = resp.usage
        inp = usage.prompt_tokens if usage else 0
        out = usage.completion_tokens if usage else 0
        logger.info("openai/%s: %d in %d out %.1fms $%.6f", self.config.model, inp, out, elapsed, _est(self.config.model, inp, out))
        return data
